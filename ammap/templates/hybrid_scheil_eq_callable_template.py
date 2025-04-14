#NOT YET PROPERLY TEMPLATED
# 
# STEP 1 - SCHEIL SIMULATION
#TODO - ensure proper naming seperation from pure Scheil, 
from scheil import simulate_scheil_solidification
from pycalphad import Database,equilibrium, variables as v
from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
from pycalphad.codegen.callables import build_phase_records
import pandas as pd
import math

dbf = Database("{tdb_file}")
T = {scheil_start_temperature} #name
elementalSpaceComponents = {elements}

phases = list(set(dbf.phases.keys()))
comps = [s.upper() for s in elementalSpaceComponents] + ['VA']
phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
models = instantiate_models(dbf, comps, phases_filtered)
phase_records = build_phase_records(dbf, comps, phases_filtered, {{v.N, v.P, v.T}}, models=models)

liquid_phase_name = '{liquid_phase_name}'
step_temperature = {step_temperature}

#TODO - ensure proper naming seperation from pure equilibrium

# Stop point of equilibrium based on Scheil
eT = {equilibrium_temperature_min}
# Possible Point of Error below if T range is wrong (T Equilibrium)
expected_conds=[v.T]+[v.X(el) for el in comps[:-2]]
default_conds={{v.P: {pressure}, v.N: 1.0}}

# Generate feasible phases list
feasible_phases = {feasible_phases}

def hybrid_callable(elP):
    elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
    initial_composition = dict(zip([v.X(el) for el in comps[:-2]], elP_round))
    
    sol_res = simulate_scheil_solidification(
        dbf, comps, phases_filtered,
        initial_composition, T, step_temperature=step_temperature)

    phaseFractions = {{}}
    for phase, amounts in sol_res.cum_phase_amounts.items():
        finalAmount = round(amounts[-1], 6)
        if finalAmount > 0:
            phaseFractions[phase] = finalAmount
    
    test = sol_res.cum_phase_amounts
    Lfrac = sol_res.fraction_liquid
    Sfrac = sol_res.fraction_solid
    scheilT = sol_res.temperatures
    solT = scheilT[-1]
    ddict = sol_res.x_phases
    
    keys_to_remove_from_ddict = []
    for ddict_key, dict_value in ddict.items():
        keys_to_remove_from_dict = [key for key, value in dict_value.items() if pd.isna(value).all()]
        for key in keys_to_remove_from_dict:
            del dict_value[key]   
        if not dict_value:
            keys_to_remove_from_ddict.append(ddict_key)
    
    for key in keys_to_remove_from_ddict:
        del ddict[key]
    
    yPhase = sol_res.Y_phases
    liqT = next((temp for temp, frac in zip(scheilT, Lfrac) if frac < 1), scheilT[-1])
    
    # Scheil results, WRONG (maybe????)
    {{
    'scheilT': scheilT,
    'finalPhase': phaseFractions,
    'Lfrac': Lfrac,
    'Sfrac': Sfrac,
    'solT': solT,
    'liqT': liqT,
    'phaseFractions': test,
    'xPhase': ddict
    }}
    # Start EQ

    conds = {{**default_conds, **dict(zip(expected_conds, [T] + elP_round))}}
    eq_res = equilibrium(
        dbf, comps, phases_filtered,
        conds, model=models, phase_records=phase_records, calc_opts=dict(pdens=5000))
    
    nPhases = eq_res.Phase.data.shape[-1]
    phaseList = list(eq_res.Phase.data.reshape([nPhases]))
    phasePresentList = [pn for pn in phaseList if pn!='']
    
    if len(phasePresentList)==0:
        pass
    
    pFrac=eq_res.NP.data.shape[-1]
    pFracList=list(eq_res.NP.data.reshape([nPhases]))
    pFracPresent= [pn for pn in pFracList if not math.isnan(pn)]
    
    return{{
        'Phases':phasePresentList,
        'PhaseFraction':pFracPresent
    }}
    }}


# STEP 2 - FORMAT SCHEIL OUTPUT LIKELY ALL TO BE UNUSED
#TODO largely unneeded, but double check to ensure that is the case
#  this code is to read the transfer the TC output into readable excel sheet
# prepare for step 3, where the local composition at different solid fraction will be calculated
# this one will read in wt%-based data, as shown in line 218-220, changing to mol% might need small modification

import pandas as pd
import numpy as np
from tqdm import tqdm
from sklearn import neighbors
import os
from sklearn import neighbors
import pandas as pd


def getCompositions(fileName): # get the compositions from the TC output file
    PhaseNames = []
    f = open(fileName,'r')
    lines = f.readlines()
    result = dict()
    currphase = None
    currele = None
    start = False
    for i in range(len(lines)):
        line = lines[i]
        words = line.split()
        if words == ['BLOCKEND']:
            start = False
        if len(words) >= 2 and 'W(' in words[-1] and words[0] == '$':
            start = False
            currphase = words[-1].split(',')[0][2:]
            currele = words[-1].split(',')[1][:-1]
            if currphase not in result.keys():
                result[currphase] = dict()
                # result[currphase]['Temperature'] = []
            if currele not in result[currphase].keys():
                result[currphase][currele] = []
        if currphase != None and currele != None:
            if len(words) != 0 and words[-1] == 'M':
                start = True
        if start and len(words) >= 2:
            # print(line,i)
            # result[currphase]['Temperature'].append(float(words[0]))
            result[currphase][currele].append((float(words[0]),float(words[1])))
    return result
#########################################################
# comp = {Phase1, Phase2, Phase3...}
# Phase1 = {ele1, ele2, ele3...}
# ele1 = [(temp1, concentration),(temp, concentration)...]
#########################################################
# finalPhases[Phase1,Phase2]
# Phase1 = ([phaseAmount], [temperature])
def linkSolidtoComp(finalPhases, comp, eles): # I asked TC to output one file with Temperature vs Solid Fraction, one file with Temperature vs Liquid Fraction, and one file with Temperature vs Composition, here we use temprature to link all the outputs
    # Models = {Phase1, Phase2, Phase3}
    # Phase1 = {ele1, ele2, ele3}
    ## ele1 = model1
    # ele1 = [model1, model2]
    # model1: T -> compp
    # model2: T -> phaseAmount
    n_neighbors = 2
    weights = 'distance'
    Models = {}
    for phase in finalPhases.keys():
        Models[phase] = {}
        for ele in eles:
            try:
                T1 = [item[0] for item in comp[phase][ele]]
                comp1 = [item[1] for item in comp[phase][ele]]
                T2 = finalPhases[phase][1]
                phaseAmount2 = finalPhases[phase][0]
                model1 = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(T1) .reshape(-1, 1), comp1)
                model2 = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(T2) .reshape(-1, 1), phaseAmount2)
                Models[phase][ele] = (model1, model2)
            except:
                continue
    return Models

def getPhaseNamesInSequence(fileName): # go through the TC output file to get the phase form during the solidification process
    PhaseNames = []
    f = open(fileName,'r')
    lines = f.readlines()
    for i in range(len(lines)):
        words = lines[i].split()
        if words != [] and words[0] == '$E' and len(words) > 1:
            phase = words[1:]
            if 'LIQUID' not in phase[0] and phase[0] not in PhaseNames:
                PhaseNames.append(phase[0])
            # if 'LIQUID#' in phase[0] and phase[0] not in PhaseNames:
            #     PhaseNames.append(phase[0])
    f.close()
    return PhaseNames

    # phases = []
    # i = 0
    # for item in data:
    #     temptList = [thing for thing in item.keys()]
    #     phases += temptList
    #     if 'LIQUID#2' in temptList:
    #         print(i)
    #     i += 1
    # phases = set(phases)
    # return phases

def getScheilPhases(fileName): # phase amount as a funcion of temperature from TC output file
    # print(f'Reading {index}th file')
    try:
        phaseNames = getPhaseNamesInSequence(fileName)
        # if int(fileName.split('/')[-1].split('_')[0]) in [132, 133, 136, 138, 170, 171, 172, 175, 207, 208, 209, 210, 239, 240, 241, 244, 245, 246, 274, 275, 279, 280, 281, 282, 314, 315, 316, 320, 342, 343, 344, 348, 349, 353, 375, 376, 377, 380, 381, 382, 407, 410, 411, 412, 413, 438, 439, 442, 443, 468, 498, 609, 735, 769, 796, 799, 809, 810, 835, 865]:
        #     phaseNames.append('SIGMA')
        data = open(fileName,'r')
    except:
        print(f'{fileName} does not exist, skip')
        Phases = dict()
        Temperatures = dict()
    # print('Related phases:', phaseNames)
    try:
        currentPhases = dict()
        currentTemp = dict()
        for phase in phaseNames:
            currentPhases[phase] = []
            currentTemp[phase] = []
        startBlock = False
        startRead = False
        BlockNum = 0
        lines = data.readlines()
        for i in range(len(lines)):
            words = lines[i].split()
            if words != [] and words[:2] == ['$','BLOCK']:
                BlockNum += 1
                startBlock = True
                phaseCount = 0
            if startBlock and words != [] and words[-1] == 'M':
                startRead = True
            if startRead and words != [] and words == ['CLIP', 'OFF']:
                startRead = False
                phaseCount += 1
            if startRead and words != [] and words[:2] == ['$', 'Y-AXIS:']:
                startRead = False
                phaseCount += 1            
            if startRead and startBlock and words != [] and words[0] == 'BLOCKEND':
                startRead = False
                startBlock = False
            if startRead:
                phase = phaseNames[phaseCount]
                currentTemp[phase].append(float(words[0]))
                currentPhases[phase].append(float(words[1]))

        Phases = currentPhases
        Temperatures = currentTemp
    except Exception as e:
            print(f'fail to read {fileName}, skip',e)
            Phases = dict()
            Temperatures = dict()

    phaseNames = [item for item in Phases.keys()]
    # print('All related phases:', phaseNames)
    finalPhases = dict()
    for phase in phaseNames:
        finalPhases[phase] = []
    list = []
    phaseAmount = Phases
    if phaseAmount != dict():
        for phase in phaseNames:
            finalPhases[phase] = (phaseAmount[phase],Temperatures[phase])
    return finalPhases
# finalPhases[Phase1,Phase2]
# Phase1 = ([phaseAmount], [temperature])
def readScheil(fileName): # get the temperature and solid fraction from TC output file
    # temperature = []
    # liquidFraction = []
    # Solidtemp = []
    # Liquidtemp = []
    # indexs = []
    temp = []
    liquid = []
    try:
        data = open(fileName,'r')
    except:
        print(f'cannot find {fileName}')
        return [],[]
    lines = data.readlines()
    startRead = False
    for i in range(len(lines)):
        content = lines[i]
        words = content.split()
        if i < len(lines) - 1:
            nextContent = lines[i + 1]
            # print(words[-1],',', nextContent,'/n')
        if words!= [] and words[-1] == 'M':
            startRead = True
        if words == ['BLOCKEND'] or words == ['CLIP', 'OFF'] or words[:2] == ['$', 'Y-AXIS:'] and startRead:
            startRead = False
        if startRead:
            temp.append(float(words[0]))
            liquid.append(float(words[1]))
    temperature = temp
    liquidFraction = liquid
    solidFraction = []
    for item in liquidFraction:
        solidFraction.append(1-item)
    return solidFraction, temperature
###############################################################
# comps, eleComp = linkSolidtoComp(solidFraction, temperature, AllComp, ele)

def processScheilResults(simulationPath,numFile): #use all the above functions to make the TC output readable, save them in excel sheets
    ################################################################################
    #==============================================================================#
    ##############################get settings######################################
    folder_Scheil = f'{simulationPath}/Scheil Simulation'
    isExist = os.path.exists(folder_Scheil + '/Result')
    if not isExist:
        os.makedirs(folder_Scheil + '/Result')
        print("The new directory is created!")
    isExist = os.path.exists(folder_Scheil + '/Result/ReadableOutput')
    if not isExist:
        os.makedirs(folder_Scheil + '/Result/ReadableOutput')
        print("The new directory is created!")
    output_folder = folder_Scheil + '/Result/ReadableOutput'
    ################processing########################
    for i in tqdm(range(numFile)):
        output = dict()
        fileName = f'{folder_Scheil}/{i}_composition_wt%.exp'
        fileName2 = f'{folder_Scheil}/{i}_solid_wt%.exp'
        fileName3 = f'{folder_Scheil}/{i}_liquid_wt%.exp'
        try:
            comp = getCompositions(fileName)
            finalPhases = getScheilPhases(fileName2)
            solidFraction, temperature_total = readScheil(fileName3)
            eles = [item for item in comp['LIQUID'].keys()]
            Models = linkSolidtoComp(finalPhases, comp, eles)
            output['Temperature (C)'] = temperature_total
            output['Solid Fraction (wt)'] = solidFraction
            # Models = {Phase1, Phase2, Phase3}
            # Phase1 = {ele1, ele2, ele3}
            ## ele1 = model1
            # ele1 = [model1, model2]
            # model1: T -> compp
            # model2: T -> phaseAmount
            for phase in Models.keys():
                output[phase + ' (wt)'] = Models[phase][eles[0]][1].predict(np.array(temperature_total).reshape(-1, 1))
            for phase in Models.keys():
                for ele in eles:
                    output[phase + '-' + ele + ' (wt)'] = Models[phase][ele][0].predict(np.array(temperature_total).reshape(-1, 1))
            output = pd.DataFrame(output)
            output.to_csv(f'{output_folder}/{i}_output.csv', index=False)
        except Exception as e:
            print(f'Fail for {i}th simulation',e)

################################################# INPUT REGION  #############################################################
# path to project, don't need to put '/Schiel Simulation' at the end
path = './Ti-Cr_Demo'
numFile = 41 # number of Scheil simulation, i.e., compositions in your comoposition file
pathCompositionFile = './Ti-Cr composition.xlsx'
processScheilResults(path,numFile)

###



#STEP 2.5 Reading Scheil Output
#TODO convert reading excel to just the scheil json
###
# This code is the reading scheil part
# input part
numFile = 41 # number of compositions in the composition path file
path = './Ti-Cr_Demo'
isExist = os.path.exists(path + '/Hybrid Scheil-Eq')
if not isExist:
    os.makedirs(path + '/Hybrid Scheil-Eq')

def findPhases(data): # find the related phases in the excel sheet generated in step2
    heads = data.columns
    result = []
    for item in heads:
        if 'SOLID' not in item.upper() and 'TEMPERATURE' not in item.upper() and '-' not in item:
            item2 = item[:-5]
            result.append(item2)
    return result
def findEles(data): # find the related elements in the excel sheet generated in step2
    phases = findPhases(data)
    phase = phases[0]
    heads = data.columns
    result = []
    for item in heads:
        if '-' in item and phase in item:
            item2 = item.split('-')
            result.append(item2[1][:-5])
    return result

def getSolidComposition(data): # get the "local" (solid fraction-based) phase amount and solid composition at different solid fractions
    phaseresult = dict()
    phases = findPhases(data)
    print(phases)
    for phase in phases:
        phaseresult[phase] = []
    eles = findEles(data)
    print(eles)
    solidFrac = [item for item in data['Solid Fraction (wt)'].values]
    length = len(data[f'{phases[0]} (wt)'].values)
    print('original length:',length)
    SolidComposition = dict()
    SolidComposition['SolidFrac'] = []
    for ele in eles:
        SolidComposition[ele] = []
    for index in range(length):
        isZero = False
        if index > 1 and solidFrac[index] == solidFrac[index - 1]:
            continue
        else:
            for ele in eles:
                total = 0
                if index != 0:
                    phaseAmounts = []
                    for phase in phases:
                        phaseAmount1 = data[f'{phase} (wt)'].values[index]
                        phaseAmount2 = data[f'{phase} (wt)'].values[index-1]
                        phaseAmounts.append(phaseAmount1 - phaseAmount2)
                    totalSolid = 0
                    for item in phaseAmounts:
                        totalSolid += item
                else:
                    phaseAmounts = []
                    for phase in phases:
                        phaseAmount1 = data[f'{phase} (wt)'].values[index]
                        phaseAmount2 = 0
                        phaseAmounts.append(phaseAmount1 - phaseAmount2)
                    totalSolid = 0
                    for item in phaseAmounts:
                        totalSolid += item
                if totalSolid == 0:
                        isZero = True
                else:
                    i = 0
                    for phase in phases:
                        phaseFrac = phaseAmounts[i] / totalSolid
                        eleAmount = data[f'{phase}-{ele} (wt)'].values[index]
                        total += phaseFrac *  eleAmount
                        i += 1
                    SolidComposition[ele].append(total)
            if not isZero:
                i = 0
                for phase in phases:
                    phaseFrac = phaseAmounts[i] / totalSolid
                    phaseresult[phase].append(phaseFrac)
                    i += 1
                SolidComposition['SolidFrac'].append(solidFrac[index])

    return SolidComposition, phaseresult

def processData(comp, phase): # remove the outliers in the data, should not remove too much, otherwise need to check the simulation
    length = len(comp['SolidFrac'])
    print('before processing:',length)
    indexs = []
    for index in range(length):
        isOutlier = False
        if index > 1 and index < length - 2:
            for item in comp.keys():
                if 'SOLID' not in item.upper() and 'TEMPERATURE' not in item.upper():
                    diff1 = abs(comp[item][index] - comp[item][index-1])
                    diff2 = abs(comp[item][index] - comp[item][index+1])
                    if diff1/comp[item][index-1] > 0.1 and diff2/comp[item][index+1] > 0.1 and max(diff1, diff2) > 0.1: # if the point is very different from the previous and next data point, drop it
                        isOutlier = True
        if not isOutlier:
            indexs.append(index)
    result1 = dict()
    for item in comp.keys():
        result1[item] = []
    result2 = dict()
    for item in phase.keys():
        result2[item] = []
    for index in indexs:
        for item in result2.keys():
            result2[item].append(phase[item][index])
        for item in result1.keys():
            result1[item].append(comp[item][index])
    print('after processing:',len(result1['SolidFrac']))
    return result1, result2
        
# considered making mole-based input or mass-based input as an option, but never worked on it
# this function is not used anywhere
def MoleToMass(SolidComp):
    result = dict()
    result['SolidFrac'] = SolidComp['SolidFrac']
    for ele in SolidComp.keys():
        if ele != 'SolidFrac':
            result[ele] = []
    eleTable = {'Ni':58.71, 'Cr':51.996, 'Fe':55.847, 'Nb':92.906, 'Mo':95.94, 'Cu':63.546, 'V':50.9415,'C':12.011,'Ti':47.867,'Al':26.9815,'Si':28.0855,'Mn':54.938,'Co':58.9332,'Zn':65.38,'P':30.9738,'S':32.065,'B':10.811,'N':14.0067,'O':15.9994,'H':1.00794,'Ca':40.078,'Mg':24.305,'Sr':87.62,'Ba':137.327,'Zr':91.224,'Sn':118.71,'Pb':207.2,'As':74.9216,'Sb':121.76,'Bi':208.98,'Se':78.96,'Te':127.6,'W':183.84,'Ta':180.948,'Re':186.207,'Hf':178.49,'Pt':195.084,'Au':196.967,'Pd':106.42,'Ag':107.868,'Rh':102.906,'Ir':192.217,'Ru':101.07,'La':138.905,'Ce':140.116,'Pr':140.908,'Nd':144.}
    for i in range(len(SolidComp['SolidFrac'])):
        sum = 0
        for ele in SolidComp.keys():
            if ele != 'SolidFrac':
                sum += SolidComp[ele][i] * eleTable[ele]
        for ele in SolidComp.keys():
            if ele != 'SolidFrac':
                result[ele].append(SolidComp[ele][i] * eleTable[ele] / sum * 100)
    return result

for index in range(numFile): # with all the above functions, process the data and save the data to the output folder
    problemList = []
    fileName = f'{index}_output.csv'
    try:
        data = pd.read_csv(path + '/Scheil Simulation/Result/ReadableOutput/' + '' + fileName)
        print('#######################################')
        print(index)
        SolidComp, phaseresult = getSolidComposition(data)
        data2 = pd.DataFrame(SolidComp)
        data2.to_excel(path + '/Hybrid Scheil-Eq/' + f'{fileName.split("_")[0]}_comp.xlsx')
        SolidComp, phaseresult = processData(SolidComp, phaseresult)
        file2 = pd.DataFrame(phaseresult)
        file2.to_excel(path + '/Hybrid Scheil-Eq/' + f'{fileName.split("_")[0]}-phase.xlsx',index = False)
        data2 = pd.DataFrame(SolidComp)
        data2.to_excel(path + '/Hybrid Scheil-Eq/' + f'{fileName.split("_")[0]}_comp.xlsx',index = False)
    except Exception as e:
        problemList.append(fileName)
        print(f'{index} has problem: {e}')
    print('#######################################')
    print(f'problemList: {problemList}')


    # not ready, becasue in previous step2, it read in wt-based data. haven't link the codes yet
    # if 'Mole' in AmountEle:
    #     SolidComp = MoleToMass(SolidComp)
    #     data2 = pd.DataFrame(SolidComp)
    #     data2.to_excel(f'{fileName[:-5]}_comp.xlsx')
    # plot(data,SolidComp,phaseresult,fileName)

    ###





    ### Step 3 - Equilibrium based on Scheil
# #TODO - ensure proper naming seperation from pure equilibrium

# from pycalphad import Database, equilibrium, variables as v
# from pycalphad.core.utils import instantiate_models, filter_phases, unpack_components
# from pycalphad.codegen.callables import build_phase_records
# import math

# dbf = Database("{tdb_file}")
# T = {temperature}
# elementalSpaceComponents = {elements}

# phases = list(set(dbf.phases.keys()))
# comps = [s.upper() for s in elementalSpaceComponents]+['VA']
# phases_filtered = filter_phases(dbf, unpack_components(dbf, comps), phases)
# models = instantiate_models(dbf, comps, phases_filtered)
# phase_records = build_phase_records(dbf, comps, phases_filtered, {{v.N, v.P, v.T}}, models=models)

# expected_conds=[v.T]+[v.X(el) for el in comps[:-2]]
# default_conds={{v.P: {pressure}, v.N: 1.0}}

# # Generate feasible phases list
# feasible_phases = {feasible_phases}

# def equilibrium_callable(elP):
#     elP_round = [round(v-0.000001, 6) if v>0.000001 else 0.0000001 for v in elP]
#     conds = {{**default_conds, **dict(zip(expected_conds, [T] + elP_round))}}
#     eq_res = equilibrium(
#         dbf, comps, phases_filtered,
#         conds, model=models, phase_records=phase_records, calc_opts=dict(pdens=5000))
    
#     nPhases = eq_res.Phase.data.shape[-1]
#     phaseList = list(eq_res.Phase.data.reshape([nPhases]))
#     phasePresentList = [pn for pn in phaseList if pn!='']
    
#     if len(phasePresentList)==0:
#         pass
    
#     pFrac=eq_res.NP.data.shape[-1]
#     pFracList=list(eq_res.NP.data.reshape([nPhases]))
#     pFracPresent= [pn for pn in pFracList if not math.isnan(pn)]
    
#     return{{
#         'Phases':phasePresentList,
#         'PhaseFraction':pFracPresent
#     }}




### Step 4 - Correct Outputs


if __name__ == "__main__":
    pass