# -*- coding: utf-8 -*-
"""
Created by Gather Lab

This is the code for the analysis of EL measurements. It corrects the IVL measurement for non-Lambertian emission. The spectral intensities within 180deg (or 90deg)
were measured with the spectrometer and from this the characteristics is corrected. 
For the analysis the data from 0 to 90deg is considered (not-90 to 0deg), care should be taken that the cut-out of the holder is positioned accordingly.

Required files:
	- 'library' folder with 
		- "Responsivity_PD.txt" 
		- "Photopic_response.txt"
		- "NormCurves_400-800.txt"
		- 'CalibrationData.txt'(converison from counts into intensity)
	- 'data' folder
	  with sample folder
		-'batch' folder
		with sample folder again
	- in both sample folders:
			'datetime' folder
				'raw' folder
					'keithleydata' and 'spectrumdata' folder
						*'keithleydata' there should be the files: keithleyOLEDvoltages.txt, keithleyPDvoltages.txt, specifickeithleyPDvoltages.txt
						For ANALYSIS especially the keithleyPDvoltages.txt file can be copied into the folder as a PD measurement might not be needed for every single device
						*'spectrumdata' there should be the text files (depending on your recodring choice) from Angle-90.txt over Angle0.txt to Angle90.txt
						AND a background file (all recorded within the run)				

The default values for the parameters in this code are          
	- distance of PD and OLED 0.115m
	- PDarea = 0.000075 # m2; area of the used photodiode
	- PDres = 4.75e5 # Ohm; at 50dB gain
		   
The output of this program is created in the sample folder in the 'data' folder (sample folder in 'batch' is kept unchanged):    
    - creates a 'processedEL' folder with the results
		'sample_name'_effdata_LAM.txt
			Measurement code : 'sample name''datetime'
			Calculation programme :	NonLamLIV-EQE_vfinal.py
			Credits :	GatherLab, University of St Andrews, 2020
			Measurement time : 201907031258	Analysis time :201907031524
			OLED active area:     4e-06 m2
			Distance OLED - Photodiode:   0.115 m
			Photodiode area:    7.54296396127e-05m2
			Maximum intensity at:     570.0 nm
			CIE coordinates:      (0.522, 0.476)
			V            I           J         Abs(J)        L         EQE        LE         CE        PoD
		'sample_name'_effdata_NONLAM.txt
			V            I           J         Abs(J)        L         AvLum    EQE        LE         CE        PoD
		'sample_name'_lamdata.txt (this includes not only the angle-dependent emission but also a correction for the photopic response due to spectral changes)
		'sample_name'_specdata.txt
		'sample_name'_specdatafull_LAM.txt
		'sample_name'_specdatahalf.txt
		and
		7 PNG files containing some of the comparison between NONLAM and LAM.

Important parameters for the analysis:    
    - distance PD to OLED: fixed in EL setup to 0.115m
    - PD paramters: PDA100A2 (area: 75mm2, PDgain (usually 50dB))
	- size of OLED

"""

"IMPORTING REQUIRED MODULES"
# General Modules
import os, shutil
import re, string
import numpy as np
import matplotlib.pyplot as mpl
import datetime as dt

"FUNCTIONS AND DEFAULT SETTINGS"
def movingaverage(interval, window_size):
    """
    Smoothing function
    """
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')

def set_gain(gain):
    """
    Set calculation parameters according to gain of photodiode.

    gain: int (0, 10, 20, 30, 40, 50, 60, 70)
        Gain of photodiode which was used to measure the luminance.

    returns:
        PDres: float
            resistance of the transimpedance amplifier used to amplify and
            convert the photocurrent of the diode into a voltage.
        PDcutoff: float
            cutoff voltage of photodiode below which only noise is expected.
    """
    if gain == 0:  # set resistance of the transimpedance amplifier used to amplify and convert PD current into voltage
        PDres = 1.51e3  # Ohm; High-Z
        PDcutoff = 1e-6  # V
    elif gain == 10:
        PDres = 4.75e3  # Ohm; High-Z
        PDcutoff = 3e-6  # V
    elif gain == 20:
        PDres = 1.5e4  # Ohm; High-Z
        PDcutoff = 5e-6  # V
    elif gain == 30:
        PDres = 4.75e4  # Ohm; High-Z
        PDcutoff = 1e-5  # V
    elif gain == 40:
        PDres = 1.51e5  # Ohm; High-Z
        PDcutoff = 3e-4  # V
    elif gain == 50:
        PDres = 4.75e5  # Ohm; High-Z
        PDcutoff = 9e-4  # V
    elif gain == 60:
        PDres = 1.5e6  # Ohm; High-Z
        PDcutoff = 4e-3  # V
    elif gain == 70:
        PDres = 4.75e6  # Ohm; High-Z
        PDcutoff = 2e-3 # V
    elif gain == 80:
        PDres = 2.2e6  # Ohm; High-Z
        PDcutoff = 2e-5 # V
            
    else:
        print('Error: Not a valid gain.' +
              '\nThe Thorlabs PDA100A2 supports the following gains:' +
              '\n0 dB, 10 dB, 20 dB, 30 dB, 40 dB, 50 dB, 60 dB, 70 dB' +
              '\nCheck photodiode gain in your data header.')
    return PDres, PDcutoff

"SETTING KNOWN PARAMETERS"
now = dt.datetime.now() # Set the start time
start_time = str(now.strftime("%Y-%m-%d %H:%M").replace(" ","").replace(":","").replace("-",""))

# Loading the V(λ) and R(λ) spectra against wavelength
wavelength = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','Photopic_response.txt'))[:,0]
Vlambda = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','Photopic_response.txt'))[:,1]
Rlambda = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','Responsivity_PD.txt'))[:,1] 

# Loading the CIE Normcurves
XCIE = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','NormCurves_400-800.txt'))[:,2]
YCIE = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','NormCurves_400-800.txt'))[:,3]
ZCIE = np.loadtxt(os.path.join(os.path.dirname(__file__),'library','NormCurves_400-800.txt'))[:,4]

# Loading the spectrometer calibration factors -  this converts the counts/nm/sr into W/nm/sr (responsivity function of the spectrometer and transmission of the fibre)
calibrationwvl = np.array(np.loadtxt(os.path.join(os.path.dirname(__file__),'library','CalibrationData.txt'))[:,0])
calibration = np.array(np.loadtxt(os.path.join(os.path.dirname(__file__),'library','CalibrationData.txt'))[:,1])
calibration = np.interp(wavelength, calibrationwvl, calibration) # interpolate calibration factor onto correct axis

# Setting Variables
OLEDwidth = 2e-3 # OLED width or height in m; 
OLEDarea = (OLEDwidth)**2 
PDarea = 0.000075  #Photodiode area in m2
PDradius = np.sqrt(PDarea / np.pi) # Photodiode Radius in m
PDresis, PDcutoff = set_gain(70)  # Resistance if gain = 70dB and high load resistance
distance = 0.115 # Distance between OLED and PD in m 
sqsinalpha = PDradius**2/(distance**2 + PDradius**2) # Taking into account finite size of PD

# Setting Constants
Km = 683 # Peak response in lm/W 
h = 6.62606896e-34 # Planck's Constant in Js
c = 299792458 # Speed of Light in m/s
e = 1.602176462e-19 # Magnitude of fundamental charge in As

batch = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'batch'))
print os.listdir(batch)
for sample in os.listdir(batch):         
    for datetime in os.listdir(os.path.abspath(os.path.join(batch, sample))): 
        sampledirectory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', sample, datetime))
        rawdirectory = os.path.abspath(os.path.join(sampledirectory, 'raw')) 
        if os.path.isdir(rawdirectory):
            pass
        else:
            print "No data found for this measurement code."
            os.sys.exit()

        "SETTING DIRECTORY FOR EXPORTING DATA"
        processdirectory = os.path.abspath(os.path.join(sampledirectory, 'processedEL')) 
        process = True
        while process == True:
            if os.path.isdir(processdirectory):
                cont = 'Y' # str(raw_input("Processed data already exists for this measurement code. Proceed with analysis? (Y/N)  "))
                if cont == str('Y'):
                    cont =  'Y' # str(raw_input("Do you wish to overwrite current analysis data? (Y/N)   "))
                    if cont == str('Y'):
                        s = open(os.path.join(processdirectory,'_specdata.txt'), 'w')
                        s.close() # Makes sure the file is closed before deleting the folder
                        shutil.rmtree(processdirectory)
                        os.mkdir(processdirectory)
                        process = False
                        break
                    elif cont == str('N'):
                        for n in range(1,5,1): # Makes a new directory with a different name so the old one isn't overwritten
                            process = 'processed' + str(n)
                            processdirectory = os.path.abspath(os.path.join(sampledirectory, process)) 
                            if not os.path.isdir(processdirectory):
                                os.mkdir(processdirectory)
                                process = False
                                break                
                    else:
                        print "Invalid input."
                elif cont == str('N'):
                        print "Finished. No analysis performed."
                        os.sys.exit()
                else:
                    print "Invalid input."
            else:
                os.makedirs(processdirectory)
                process = False
                break
        
        "FINDING EXISTING DATA AND PERFORMING ANALYSIS"        
        mayafilepath = 'spectrumdata' # setting spectra directory        
        keithleyfilepath = 'keithleydata' # setting keithley directory
        mayafilepath = os.path.abspath(os.path.join(rawdirectory, mayafilepath))
        keithleyfilepath = os.path.abspath(os.path.join(rawdirectory, keithleyfilepath))
        spec_header = 11 
        voltage_header = 11        
        print "Spectrum files found for this measurement :   ", os.listdir(mayafilepath)
        print "Keithley files found for this measurement :   ", os.listdir(keithleyfilepath)
        
        print "\nIMPORTING DATA..."                    

        # Importing spectrum data
        mayadata = os.listdir(mayafilepath) # lists all files in folder spectrum data
        spectrumdata = [ a for a in mayadata if a.startswith('Angle') ]
        background = [ a for a in mayadata if not a.startswith('Angle') ]
        spectrumdata.sort(key = lambda x : (float(x.split("Angle")[1].split(".txt")[0]), x))
        print "\nSpectrum files in use are: ", spectrumdata
        print "\nBackground file in use is:", background                                                        
        # Background spectrum
        bgwvl = np.array(np.loadtxt(os.path.join(mayafilepath, background[0]),skiprows=spec_header)[:,0]) # Loading background spectrum
        bginte = np.array(np.loadtxt(os.path.join(mayafilepath, background[0]),skiprows=spec_header)[:,1]) # Loading background spectrum
        bginte = np.interp(wavelength, bgwvl, bginte) # interpolate background onto correct axis
        print "\nBackground spectrum loaded..."        
        # Selecting which angle which will be read first
        first_angle = float(string.split(str(string.split(spectrumdata[0],'.txt')[0]),'Angle')[1]) # gets the string 'Angle_' from the filename
        print "\nThe first angle to be analysed is:   "+str(first_angle)+"..."
        # Saving the data for the forward spectrum
        try:
            specwvl = np.array(np.loadtxt(os.path.join(mayafilepath,'Angle0.0.txt'), skiprows=spec_header)[:,0])
            rawspecinte = np.array(np.loadtxt(os.path.join(mayafilepath,'Angle0.0.txt'), skiprows=spec_header)[:,1]) # load wavelengths and raw intensity               
            rawspecinte = np.interp(wavelength, specwvl, rawspecinte) # interpolate spectrum onto correct axis            
            spec = np.array(rawspecinte) - np.array(bginte) # subtract background intensity
            intensity = spec * calibration # multiply by spectrometer calibration factor to get intensity in W/nm/sr
            perp_intensity = movingaverage(intensity,10)
            print "\nPerpendicular spectrum loaded..."
        except:
            try:
                specwvl = np.array(np.loadtxt(os.path.join(mayafilepath,'Angle000.txt'), skiprows=spec_header)[:,0])
                rawspecinte = np.array(np.loadtxt(os.path.join(mayafilepath,'Angle000.txt'), skiprows=spec_header)[:,1]) # load wavelengths and raw intensity               
                rawspecinte = np.interp(wavelength, specwvl, rawspecinte) # interpolate spectrum onto correct axis            
                spec = np.array(rawspecinte) - np.array(bginte) # subtract background intensity
                intensity = spec * calibration # multiply by spectrometer calibration factor to get intensity in W/nm/sr
                perp_intensity = movingaverage(intensity,10)
                print "\nPerpendicular spectrum loaded..."
            except:
                print("No perpendicular spectrum. Unable to perform analysis.")
                os.sys.exit() 
        
        # Importing current-voltage-luminance data
        angles = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyOLEDvoltages.txt'), skiprows=voltage_header)[:,0])
        OLEDvoltage_spec = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyOLEDvoltages.txt'), skiprows=voltage_header)[:,1])
        OLEDcurrent_spec = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyOLEDvoltages.txt'), skiprows=voltage_header)[:,2])                        
        # Loading the Keithley data
        currentdata = os.listdir(keithleyfilepath)
        currentdata.sort()
        OLEDdata = currentdata[0]
        PDdata = currentdata[1]
        print "\nOLED Current and Voltage file in use is:", OLEDdata
        print "\nPhotodiode Voltage file in use is:", PDdata
        # Current / Voltage / Luminance IVL Readings from Photodiode
        OLEDvoltage = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyPDvoltages.txt'), skiprows=voltage_header)[:,0])
        OLEDcurrent_mA = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyPDvoltages.txt'), skiprows=voltage_header)[:,1])
        OLEDcurrent = OLEDcurrent_mA * 1e-3
        PDvoltage = np.array(np.loadtxt(os.path.join(keithleyfilepath,'keithleyPDvoltages.txt'), skiprows=voltage_header)[:,2])
        # This checks for 180 or 90 degree measurement
        n = len(angles)-1
        min_angle = angles[0]
        max_angle = angles[n]
        step_angle = (max_angle - min_angle)/n
        print "\nSpectra taken for the following angles : ",angles
        
        print "\nPicking out the perpendicular (0 degree) reading... "
        if max_angle == 90:
            try:
                min_index = 0.0
                max_index = 90.0
            except ValueError:
               print "Can't find perpendicular reading"
        elif max_angle == 180:
            try:
                min_index = 90.0
                max_index = 180.0
            except ValueError:
               print "Can't find perpendicular reading"
        else:
            print "\nCheck angle range of data."
        
        "Setting all empty arrays for later data collection"
        ints = {}  # Dictionary for every spectrum at each angle      
        intensities = [] # 2d array of all intensities across all angles and for all wavelengths     
        Integral1 = []
        Integral2 = []
        Integral3 = []
        Integral4 = []
        eFACTOR = []
        vFACTOR = []
        RI = []
        LI = []        
        eCoeff = np.zeros(PDvoltage.shape)
        vCoeff = np.zeros(PDvoltage.shape)  
        EQE = np.zeros(PDvoltage.shape)
        Lum = np.zeros(PDvoltage.shape)
        LE = np.zeros(PDvoltage.shape)
        CE = np.zeros(PDvoltage.shape)
        POW = np.zeros(PDvoltage.shape) 
        
        # LOADING ALL OF THE SPECTRUM DATA AND FORMATTING
        for title in spectrumdata:
            name = str(string.split(title,'.txt')[0]) # gets the string 'Angle_' from the filename
            angle = float(string.split(name,'Angle')[1]) # gets the string 'Angle_' from the filename
            
            "PROCESSING THE SPECTRUM DATA - SUBTRACT BACKGROUND AND MULTIPLY BY CALIBRATION"
            specwvl = np.array(np.loadtxt(os.path.join(mayafilepath,title), skiprows=spec_header)[:,0])
            rawspecinte = np.array(np.loadtxt(os.path.join(mayafilepath,title), skiprows=spec_header)[:,1]) # load wavelengths and raw intensity               
            rawspecinte = np.interp(wavelength, specwvl, rawspecinte) # interpolate spectrum onto correct axis            
            spec = np.array(rawspecinte) - np.array(bginte) # subtract background intensity
            intensity = spec * calibration # multiply by spectrometer calibration factor to get intensity W/nm/sr
            intensity = movingaverage(intensity,10) # smoothing
            ints[angle] = intensity # saves individual spectra to a directory of all
            
            RI.append(float(h*c/1e-9*np.sum(intensity)))                
            LI.append(float(Km*h*c/1e-9*np.sum(intensity*Vlambda)))   

            if angle == first_angle: # Stacking intensities into a 2D matrix
                intensities.append((np.array(intensity)))
            else:
                intensities = np.vstack((intensities,np.array(intensity)))                    

            if angle in np.arange(min_index,max_index,step_angle):
                eFACTOR.append(sum(intensity*wavelength)/sum(perp_intensity*wavelength)) # This replaces cos(theta) in I = I0*cos(theta) 
                vFACTOR.append(sum(intensity*Vlambda)/sum(perp_intensity*Vlambda)) # This replaces cos(theta) in I = I0*cos(theta) 
              
        # Formatting the data for the intensity map and spectrum.
        specangles = np.hstack([0, angles])
        normintensities = np.array(intensities) / np.amax(np.array(intensities))
        intensitydata = np.vstack((wavelength,normintensities))
        intensitydata = np.hstack((specangles.reshape(specangles.shape[0],1), intensitydata))

        # Calculating key integrals for intensity in forward direction and correction factors F_E and F_V for all angles
        Integral1 = np.sum(perp_intensity*wavelength)
        Integral2 = np.sum(perp_intensity)
        Integral3 = np.sum(perp_intensity*Vlambda)
        Integral4 = np.sum(perp_intensity*Rlambda)
        eFACTOR = np.sum(np.array(eFACTOR)*np.sin(np.deg2rad(np.arange(min_index,max_index,step_angle)))*np.deg2rad(step_angle)) 
        vFACTOR = np.sum(np.array(vFACTOR)*np.sin(np.deg2rad(np.arange(min_index,max_index,step_angle)))*np.deg2rad(step_angle))     
        print eFACTOR
        print vFACTOR

        # Lambertian Spectrum
        Ilam = []
        for i in range(len(angles)):
            Ilam.append(np.cos(np.deg2rad(angles[i])))
        Inonlam = np.array(RI) / RI[np.where(angles == min_index)[0][0]]
        Inonlam_v = np.array(LI) / LI[np.where(angles == min_index)[0][0]] #emission in terms of photometric response, so taking into account the spectral shifts and sensitivity of the eye/photopic response
        lamdata = np.stack((angles, Ilam, Inonlam, Inonlam_v))
            
        # Current density calculations
        currentdensity = OLEDcurrent*1e3/(OLEDarea*1e4) # calculate current density in mA/cm2
        abscurrentdensity = abs(np.array(currentdensity)) # calculates the absolute value of the current density 
        
        # Calculating CIE coordinates
        for i, j in enumerate(perp_intensity):
            if j == max(perp_intensity):
                lambdamax = wavelength[i]
                X = sum(perp_intensity*XCIE)
                Y = sum(perp_intensity*YCIE)
                Z = sum(perp_intensity*ZCIE)
                CIE = [0]*2
                CIE[0] = X/(X+Y+Z)
                CIE[1] = Y/(X+Y+Z)
                CIEformatted = ('('+', '.join(['%.3f']*2)+')') % tuple(CIE)
                
        print "Calculating non-Lambertian efficiency data..."
        for v in range(len(PDvoltage)):
            if PDvoltage[v] > PDcutoff:
                eCoeff[v] = PDvoltage[v]/PDresis/sqsinalpha*2
                vCoeff[v] = Km*PDvoltage[v]/PDresis/sqsinalpha*2
                EQE[v] = 100*(e/1e9/h/c/OLEDcurrent[v]*eCoeff[v]*Integral1/Integral4*eFACTOR)
                Lum[v] = 1/np.pi/OLEDarea*vCoeff[v]/2*Integral3/Integral4
                LE[v] = 1/OLEDvoltage[v]/OLEDcurrent[v]*vCoeff[v]*Integral3/Integral4*vFACTOR
                CE[v] = OLEDarea/OLEDcurrent[v]*Lum[v]
                POW[v] = 1/(OLEDarea*1e6)*eCoeff[v]*Integral2/Integral4*eFACTOR*1e3                            
        # Formatting the efficiency data
        dataeff_NONLAM = np.stack((OLEDvoltage, OLEDcurrent*1e3, currentdensity,abscurrentdensity,Lum,EQE,LE,CE,POW))  # Converges the individual arrays into one array

        print "Calculating Lambertian efficiency data..."
        for v in range(len(PDvoltage)):
            if PDvoltage[v] > PDcutoff:
                eCoeff[v] = PDvoltage[v]/PDresis/sqsinalpha
                vCoeff[v] = Km*PDvoltage[v]/PDresis/sqsinalpha
                EQE[v] = 100*(e/1e9/h/c/OLEDcurrent[v]*eCoeff[v]*Integral1/Integral4)
                Lum[v] = 1/np.pi/OLEDarea*vCoeff[v]*Integral3/Integral4
                LE[v] = 1/OLEDvoltage[v]/OLEDcurrent[v]*vCoeff[v]*Integral3/Integral4
                CE[v] = OLEDarea/OLEDcurrent[v]*Lum[v]
                POW[v] = 1/(OLEDarea*1e6)*eCoeff[v]*Integral2/Integral4*1e3
        # Formatting the efficiency data
        dataeff_LAM = np.stack((OLEDvoltage, OLEDcurrent*1e3, currentdensity,abscurrentdensity,Lum,EQE,LE,CE,POW))  # Converges the individual arrays into one array
    
        "#####################################################################"
        "#####################EXPORTING FORMATTED DATA########################"
        "#####################################################################"
        print "\nEXPORTING..."
        
        # Header Parameters
        line01 = 'Measurement code : ' + sample + datetime
        line02 = 'Calculation programme :	NonLamLIV-EQE.py'
        linex =  'Credits :	GatherLab, University of St Andrews, 2019'
        linexx = 'Measurement time : ' + datetime + '\tAnalysis time :' + start_time
        line03 = 'OLED active area:     ' + str(OLEDarea) + ' m2'
        line04 = 'Distance OLED - Photodiode:   ' + str(distance) + ' m'
        line05 = 'Photodiode area:    ' + str(PDarea) + 'm2'
        line06 = 'Maximum intensity at:     ' + str(lambdamax) + ' nm'
        line07 = 'CIE coordinates:      ' + str(CIEformatted)
        line08 = ''
        line09 = ''
        line10 = '### Formatted data ###'
        line11 = 'V            I           J         Abs(J)        L         EQE        LE         CE        PoD'
        line12 = 'V            mA       mA/cm2      mA/cm2       cd/m2        %        lm/W        cd/A      mW/mm2'  
        line13 = 'Intensity for all Wavelengths / Angles'
        line14 = 'angles    Lambertian    Actual    Actual_v'
        line15 = 'degree    a.u.    a.u.    a.u.'
        
        
        header_lines = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line08, line09, line10, line11, line12]       
        header_lines2 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line08, line09, line10, line13]
        header_lines3 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line08, line09, line10, line14, line15]
           
        n=1             
        # Plotting an intensity grid over all angles and wavelengths
        mpl.figure(n, figsize = (10,8)) 
        intemap = mpl.contourf(angles,wavelength,normintensities.T,50,cmap=mpl.cm.jet)
        mpl.title('Normalised Intensity over all Angles and Wavelengths\n', fontsize=20)
        mpl.xlabel('Angle (degrees)', fontsize=20)
        mpl.ylabel('Wavelength (nm)', fontsize=20)
        mpl.colorbar(intemap)
        mpl.tick_params(axis='both', labelsize=20)
        mpl.savefig(os.path.join(processdirectory, sample+'_map.png'), dpi = 500)
         
        # Plotting perpendicular spectrum
        mpl.figure(n+1, figsize = (16,9))    
        mpl.plot(wavelength, perp_intensity, linewidth = 1.0, label = "Angle"+str(angle))
        mpl.title('Perpendicular Spectrum\n', fontsize=20)
        mpl.xlabel('Wavelength (nm)', fontsize=20)
        mpl.xlim(400,800) # this limits the x-range displayed,view full range before cutting down
        mpl.ylabel('Intensity (W/nm/sr)', fontsize=20)
        mpl.minorticks_on()
        mpl.grid(True, which='major', color='0.5')
        mpl.grid(True, which='minor', color='0.8')
        mpl.tick_params(axis='both', labelsize=14)
        mpl.savefig(os.path.join(processdirectory, sample+'_perpspec.png'), dpi = 500)
        
        # Plotting a combined graph of spectra at every angle
        for angle in angles:
            mpl.figure(n+2, figsize = (16,9))    
            mpl.plot(wavelength, ints[angle], linewidth = 1.0, label = "Angle"+str(angle))
            mpl.title('Angular Dependence of Spectra\n', fontsize=20)
            mpl.xlabel('Wavelength (nm)', fontsize=20)
            mpl.xlim(400,800) # this limits the x-range displayed,view full range before cutting down
            mpl.ylabel('Intensity (W/nm/sr)', fontsize=20)
            mpl.minorticks_on()
            mpl.grid(True, which='major', color='0.5')
            mpl.grid(True, which='minor', color='0.8')
        mpl.tick_params(axis='both', labelsize=14)
        mpl.savefig(os.path.join(processdirectory, sample+'_spec.png'), dpi = 500)
        np.savetxt(os.path.join(processdirectory,sample+'_specdatafull.txt'), intensitydata.T, fmt='%.6f', delimiter='\t', header='\n'.join(header_lines2), comments='')
        s = open(os.path.join(processdirectory,sample+'_specdata.txt'), 'w')
        for w in wavelength:
            s.write(str(w))
            s.write(' ')
        s.write('\n')
        for i in normintensities:
            s.write(str(i))
            s.write(' ')
        s.close()
        s = open(os.path.join(processdirectory,sample+'_specdata.txt'), 'r')
        s.close()  
         
        # Plotting Lambertian emission against Actual Emission
        mpl.figure(n+3, figsize = (10,8)) 
        mpl.plot(angles[5:-3], Inonlam[5:-3], linewidth = 1.0, label = "Actual Emission") # Actual
        mpl.plot(angles[5:-3], Inonlam_v[5:-3], linewidth = 1.0, label = "Actual Emission_v") # Actual
        mpl.plot(angles[5:-3], Ilam[5:-3], linewidth = 1.0, label = "Lambertian Emission") # Lambertian
        mpl.title('Lambertian Emission vs Actual Emission\n', fontsize=20)
        mpl.xlabel('Angle (degrees)', fontsize=20)
        mpl.ylabel('Intensity (a.u.)', fontsize=20)
        mpl.legend(loc='upper right', fontsize=14)
        mpl.tick_params(axis='both', labelsize=14)
        mpl.xlim(-90,90)
        mpl.savefig(os.path.join(processdirectory, sample+'_lam.png'), dpi = 500)
        np.savetxt(os.path.join(processdirectory,sample+'_lamdata.txt'), lamdata.T, fmt='%.2f %.4f %.4f %.4f', delimiter='\t', header='\n'.join(header_lines3), comments='')
        
        # IVL Graph
        mpl.figure(n+4, figsize = (10,8)) 
        mpl.title('IVL Characteristics\n', fontsize=20)
        fig,ax1 = mpl.subplots(figsize = (10,8))
        ax1.semilogy(OLEDvoltage, dataeff_LAM[3],'b', linewidth = 1.0, label = "Current Density") # Lambertian
        ax1.set_ylabel('Current Density (mA/cm$^2$)', color='b', fontsize=20)                                                            
        ax1.set_xlabel('Voltage (V)', fontsize=20)
        ax1.set_xlim(0,4)
        ax1.set_ylim(10e-7,10e2)
        ax2 = ax1.twinx()        
        ax2.semilogy(OLEDvoltage, dataeff_LAM[4],'r-', linewidth = 1.0, label = "Lambertian Lum") # Lambertian
        ax2.set_ylabel('Luminance (cd/m$^2$)', color='r', fontsize=20) 
        ax2.set_ylim(10e-1,10e4)
        ax1.legend(loc='upper left', fontsize=14)
        ax2.legend(loc='upper right', fontsize=14)
        ax1.tick_params(axis='both', labelsize=14)   
        ax2.tick_params(axis='both', labelsize=14)            
        mpl.savefig(os.path.join(processdirectory, sample+'_ivl.png'), dpi = 500)
        
        # EQE Graph
        mpl.figure(n+5, figsize = (10,8)) 
        mpl.title('EQE and LE\n', fontsize=20)
        fig,ax1 = mpl.subplots(figsize = (10,8))
        ax1.semilogx(dataeff_NONLAM[4], dataeff_NONLAM[5],'b', linewidth = 1.0, label = "Actual EQE") # Actual
        ax1.semilogx(dataeff_LAM[4], dataeff_LAM[5],'b-', dashes=[6, 2], linewidth = 1.0, label = "Lambertian EQE") # Lambertian
        ax1.set_ylabel('EQE (%)', color='b', fontsize=20)                                                            
        ax1.set_xlabel('Luminance (cd/m$^2$)', fontsize=20)
        ax1.set_xlim(10e0,10e3)
        ax2 = ax1.twinx()
        ax2.semilogx(dataeff_NONLAM[4], dataeff_NONLAM[6],'r', linewidth = 1.0, label = "Actual LE") # Actual
        ax2.semilogx(dataeff_LAM[4], dataeff_LAM[6],'r-', dashes=[6, 2], linewidth = 1.0, label = "Lambertian LE") # Lambertian
        ax2.set_ylabel('Luminous Efficiency (lm/W)', color='r', fontsize=20) 
        ax1.legend(loc='upper left', fontsize=14)
        ax2.legend(loc='upper right', fontsize=14)
        ax1.tick_params(axis='both', labelsize=14)   
        ax2.tick_params(axis='both', labelsize=14)    
        mpl.savefig(os.path.join(processdirectory, sample+'_eqe.png'), dpi = 500)
        
        # Densities Graph
        mpl.figure(n+6, figsize = (10,8)) 
        fig,ax1 = mpl.subplots(figsize = (10,8))
        ax1.plot(dataeff_LAM[3], dataeff_LAM[7],'b', linewidth = 1.0, label = "CE") # Lambertian
        ax1.set_ylabel('Current Efficiency (cd/A)', color='b', fontsize=20)                              
        ax1.set_xlabel('Current Density (mA/cm$^2$)', fontsize=20)                                 
        ax2 = ax1.twinx() 
        ax2.plot(dataeff_NONLAM[3], dataeff_NONLAM[8],'r', linewidth = 1.0, label = "Actual PD") # Actual
        ax2.plot(dataeff_LAM[3], dataeff_LAM[8],'r-',  dashes=[6, 2], linewidth = 1.0, label = "Lambertian PD") # Lambertian
        ax2.set_ylabel('Power Density (mW/mm$^2$)', color='r', fontsize=20)     
        ax1.legend(loc='upper left', fontsize=14)
        ax2.legend(loc='upper right', fontsize=14)
        ax1.tick_params(axis='both', labelsize=14)   
        ax2.tick_params(axis='both', labelsize=14)    
        mpl.savefig(os.path.join(processdirectory, sample+'_density.png'), dpi = 500)
               
        # Saving efficiency data
        np.savetxt(os.path.join(processdirectory,sample+'_effdata_NONLAM.txt'), dataeff_NONLAM.T, fmt='{: ^8}'.format('%.6e'), header='\n'.join(header_lines), comments='')
        np.savetxt(os.path.join(processdirectory,sample+'_effdata_LAM.txt'), dataeff_LAM.T, fmt='{: ^8}'.format('%.6e'), header='\n'.join(header_lines), comments='')

        print "FINISHED." 