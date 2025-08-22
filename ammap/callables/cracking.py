# Workspace for development of cracking critera callables.
## CURRENTLY UNDER DEVELOPMENT AND UNTESTED ##

# NEEDED inputs: solidus temperatures, liquidus temperatures, list of temperature, solid fractions
from sklearn import neighbors
import numpy as np
import math


def getFR(solidT, liquidT):
    """Freezing range criteria
    
    This function calculates the freezing range criteria by subtracting the solid temperature from the liquid temperature.
    
    Args:
        solidT (list): A list of solid temperatures.
        liquidT (list): A list of liquid temperatures.
    
    Returns:
        list: A list of freezing range criteria values. If either the solid temperature or the liquid temperature is None at a particular index, the freezing range criteria value at that index will be None.
    """
    FR = []
    for i in range(len(solidT)):
        if liquidT[i] is not None and solidT[i] is not None:
            FR.append(liquidT[i] - solidT[i])
        else:
            FR.append(None)
    return FR


def getCSC(temperature, solidFraction, CSCPoints=[0.4,0.9,0.99],numDataThreshold = 10):
    """Calculate the Critical Solidification Criteria.

    This function calculates the critical solidification criteria based on the given temperature and solid fraction.

    Args:
        temperature (list): A list of temperature values.
        solidFraction (list): A list of solid fraction values.
        CSCPoints (list, optional): A list of critical solidification criteria points. Defaults to [0.4, 0.9, 0.99].

    Returns:
        list: A list of critical solidification criteria values.
    """
    CSCPoints.sort()
    T1 = []
    T2 = []
    T3 = []
    for i in range(len(temperature)):
        Temperature = temperature[i]
        solidFrac = solidFraction[i]
        if Temperature != None and len(Temperature) >= numDataThreshold and max(solidFrac) > max(CSCPoints):
            T1.append(np.interp(CSCPoints[2], solidFrac, Temperature))
            T2.append(np.interp(CSCPoints[1], solidFrac, Temperature))
            T3.append(np.interp(CSCPoints[0], solidFrac, Temperature))
        else:
            T1.append(None)
            T2.append(None)
            T3.append(None)
    CSC = []
    for i in range(len(T1)):
        if T1[i] != None:
            try:
                CSC.append((T1[i]-T2[i])/(T2[i]-T3[i]))
            except:
                CSC.append(None)
        else:
            CSC.append(None)
    return CSC

def getKou(temperature, solidFraction, KouPoints= [0.93,0.98], numDataThreshold = 10):
    """
    Calculate the Kou value for each temperature and solid fraction pair.

    Args:
        temperature (list): A list of temperatures.
        solidFraction (list): A list of solid fractions.
        KouPoints (list): A list of Kou points.

    Returns:
        list: A list of Kou values corresponding to each temperature and solid fraction pair.
    """
    KouPoints.sort()
    T1 = []
    T2 = []
    solid1 = []
    solid2 = []
    for i in range(len(temperature)):
        Temperature = temperature[i]
        solidFrac = solidFraction[i]
        if Temperature != None and len(Temperature) >= numDataThreshold:
            T1.append(np.interp(KouPoints[1], solidFrac, Temperature))
            T2.append(np.interp(KouPoints[0], solidFrac, Temperature))
            solid1.append(KouPoints[1])
            solid2.append(KouPoints[0])
        else:
            T1.append(None)
            T2.append(None)
            solid1.append(None)
            solid2.append(None)
    Kou = []
    for i in range(len(T1)):
        if T1[i] != None:
            Kou.append(abs((T1[i]-T2[i])/((solid1[i]**0.5-solid2[i]**0.5))))
        else:
            Kou.append(None)
    return Kou

def getIntegral(temperature, solidFraction):
    """combine temperature and solid phase

    Args:
        temperature (list): list of temperature
        solidCriterion (float, optional): Defaults to 0.001.

    Returns:
        dict: combined results of T and phase fraction
    """
    result = 0
    if len(temperature) > 3:
        for i in range(len(temperature)):
            if i == 0:
                delT = abs((temperature[i+1] - temperature[i])/2)
            elif i == len(temperature) - 1:
                delT = abs((temperature[i] - temperature[i-1])/2)
            else:
                delT = abs((temperature[i+1]+temperature[i])/2-(temperature[i]+temperature[i-1])/2)
            result += solidFraction[i] * delT
    return result


def getCD(temperature, solidFraction, CDPoints = [0.7,0.98], numDataThreshold = 10):
    """
    Calculate CD1 and CD2 values based on temperature, solid fraction, and CDPoints.

    Parameters:
    temperature (list): A list of temperature values.
    solidFraction (list): A list of solid fraction values.
    CDPoints (list): A list of CD points defaulting to [0.7, 0.98].

    Returns:
    tuple: A tuple containing two lists - CD1 (srdg) and CD2 (iCSC).

    """
    CDPoints.sort()
    CD1 = []
    CD2 = []
    fs_0 = CDPoints[0]
    fs_co = CDPoints[1]
    for i in range(len(temperature)):
        Temperature = temperature[i]
        solidFrac = solidFraction[i]
        if Temperature != None and len(Temperature) >= numDataThreshold:
            T0 = np.interp(fs_0, solidFrac, Temperature)
            Tco = np.interp(fs_co, solidFrac, Temperature)
            for index in range(len(Temperature)):
                if Temperature[index] <= T0:
                    break
            Temperature = Temperature[index:]
            Temperature = Temperature[::-1]
            solidFrac = solidFrac[index:]
            solidFrac = solidFrac[::-1]
            try:
                deltT = min((T0 - Tco)/10,10)
                Trange = [item for item in np.arange(Tco,T0+deltT,deltT)]
                solidFrac_new = []
                for item in Trange:
                    solidFrac_new.append(np.interp(item, Temperature, solidFrac))
                solidFrac = [item for item in solidFrac_new if item <= fs_co]
                Trange = [Trange[i] for i in range(len(solidFrac))]
                CD1.append(getIntegral(Trange, [item**2/(1-item)**2 for item in solidFrac]))
                CD2.append(getIntegral(Trange, solidFrac))
            except:
                print(f'{i}th point cannot get sRDG and iCSC')
                print(solidFrac[0],solidFrac[-1])
                CD1.append(None)
                CD2.append(None)
        else:
            print(f'{i}th point, data point {len(Temperature) } < {numDataThreshold}')
            CD1.append(None)
            CD2.append(None)
    return CD1, CD2
#        if Temperature != None and len(Temperature) >= numDataThreshold and max(solidFrac) > max(CDPoints):
#            n_neighbors = 2
#            weights = 'distance'
#            model1 = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(Temperature).reshape(-1, 1), solidFrac)
#            model2 = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(solidFrac).reshape(-1, 1), Temperature)
#            T0 = model2.predict(np.array([fs_0]).reshape(-1, 1))[0]
#            Tco = model2.predict(np.array([fs_co]).reshape(-1, 1))[0]
#            try:
#                deltT = min((T0 - Tco)/5,0.002)
#                Trange = [item for item in np.arange(Tco,T0+deltT,deltT)]
#                solidFrac = model1.predict(np.array(Trange).reshape(-1, 1))
#                solidFrac = [item for item in solidFrac if item <= fs_co]
#                Trange = [Trange[i] for i in range(len(solidFrac))]
#                CD1.append(getIntegral(Trange, [item**2/(1-item)**2 for item in solidFrac]))
#                CD2.append(getIntegral(Trange, solidFrac))
#            except:
#                CD1.append(None)
#                CD2.append(None)
#        else:
#            CD1.append(None)
#            CD2.append(None)
#    return CD1, CD2

def getNeighborCSC(temperature, solidFraction, CSCPoints=[0.4,0.9,0.99],numDataThreshold = 10):
    """Calculate the Critical Solidification Criteria.

    This function calculates the critical solidification criteria based on the given temperature and solid fraction.

    Args:
        temperature (list): A list of temperature values.
        solidFraction (list): A list of solid fraction values.
        CSCPoints (list, optional): A list of critical solidification criteria points. Defaults to [0.4, 0.9, 0.99].

    Returns:
        list: A list of critical solidification criteria values.
    """
    CSCPoints.sort()
    T1 = []
    T2 = []
    T3 = []
    for i in range(len(temperature)):
        Temperature = temperature[i]
        solidFrac = solidFraction[i]

        if Temperature != None and len(Temperature) >= numDataThreshold and max(solidFrac) > max(CSCPoints):
            n_neighbors = 2
            weights = 'distance'
            model = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(solidFrac).reshape(-1, 1), Temperature)
            T1.append(model.predict(np.array([CSCPoints[2]]).reshape(-1, 1))[0])
            T2.append(model.predict(np.array([CSCPoints[1]]).reshape(-1, 1))[0])
            T3.append(model.predict(np.array([CSCPoints[0]]).reshape(-1, 1))[0])
        else:
            T1.append(None)
            T2.append(None)
            T3.append(None)
    CSC = []
    for i in range(len(T1)):
        if T1[i] != None:
            try:
                CSC.append((T1[i]-T2[i])/(T2[i]-T3[i]))
            except:
                CSC.append(None)
        else:
            CSC.append(None)
    return CSC

def getNeighborKou(temperature, solidFraction, KouPoints= [0.93,0.98], numDataThreshold = 10):
    """
    Calculate the Kou value for each temperature and solid fraction pair.

    Args:
        temperature (list): A list of temperatures.
        solidFraction (list): A list of solid fractions.
        KouPoints (list): A list of Kou points.

    Returns:
        list: A list of Kou values corresponding to each temperature and solid fraction pair.
    """
    KouPoints.sort()
    T1 = []
    T2 = []
    solid1 = []
    solid2 = []
    for i in range(len(temperature)):
        Temperature = temperature[i]
        solidFrac = solidFraction[i]
        if Temperature != None and len(Temperature) >= numDataThreshold and max(solidFrac) > max(KouPoints):
            n_neighbors = 2
            weights = 'distance'
            model = neighbors.KNeighborsRegressor(n_neighbors, weights=weights).fit(np.array(solidFrac).reshape(-1, 1), Temperature)
            T1.append(model.predict(np.array([KouPoints[1]]).reshape(-1, 1))[0])
            T2.append(model.predict(np.array([KouPoints[0]]).reshape(-1, 1))[0])
            solid1.append(KouPoints[1])
            solid2.append(KouPoints[0])
        else:
            T1.append(None)
            T2.append(None)
            solid1.append(None)
            solid2.append(None)
    Kou = []
    for i in range(len(T1)):
        if T1[i] != None:
            Kou.append(abs((T1[i]-T2[i])/((solid1[i]**0.5-solid2[i]**0.5))))
        else:
            Kou.append(None)
    return Kou
