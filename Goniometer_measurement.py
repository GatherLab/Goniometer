# -*- coding: utf-8 -*-
"""
created by GatherLab

This is the code for the EL and PL measurements. It is used for measurement only, 
analysis will be performed using according codes.

requires a 'data' folder

the serial number of the Keithley sourcemeter (2400series) is 04102170 --> keith_address = u'USB0::0x05E6::0x2450::04102170::INSTR'
the serial number of the multimeter (2100series) is 8003430 -->  keithmulti_address = u'USB0::0x05E6::0x2100::8003430::INSTR'

The default values for the parameters in this code are          
        318 deg # offset_angle so that OLED faces one laser diode (-90deg)
        1 deg # step_angle
        300000 microsec # integration time 300ms
        30.0 # homing_time in sec
        1.0 # moving_time in sec
        2.0  # pulse_duration in sec
		for IVL meas        
	        -2.0V  # min_voltage
			2.0V # change_voltage
			5.0V  # max_voltage
			0.5V # min_step_voltage 
            0.5V # max_step_voltage 
			1.05A  # scan_compliance
        'Current'  # as source for angle-resolved measurement, voltage works as well
		 5V # goniometer_compliance
		   
The output of this program is:    
    - creates a folder with sample name (could '190812 S23D1', 'S42D1',...)
		- creates a 'datetime' folder
			   - creates a 'raw' folder
				   - creates a 'keithleydata' and 'spectrumdata' folder
				      - in 'keithleydata' there should be the files: keithleyOLEDvoltages.txt, keithleyPDvoltages.txt, specifickeithleyPDvoltages.txt
					  For ANALYSIS especially the keithleyPDvoltages.txt file can be copied into the folder as a PD measurement might not be needed for every single device
					  BUT make sure the measurement code (first header line) is adjusted to the one from keithleyOLEDvoltages.
					  - in 'spectrumdata' there should be the text files (depending on your recodring choice) from Angle-90.txt over Angle0.txt to Angle90.txt
					  AND a background file (all recorded within the run)

Important parameters for later analysis:    
    - distance PD to OLED: fixed in EL setup to 0.115m
    - PD parameters: PDA100A2 (area: 75mm2, PDgain (usually 50dB))
	- size of OLED

required files for analysis (described later on as well):
	- 'library' folder with 
		- "Responsivity_PD.txt" 
		- "Photopic_response.txt"
		- "NormCurves_400-800.txt"
		- 'CalibrationData.txt'(converison from counts into intensity)
	- 'data' folder
		- with folders of measured data
		- a 'batch' folder with a copy of the data folder that should be analysed
"""


"#####################################################################"
"################################SETUP################################"
"#####################################################################"

"IMPORTING REQUIRED MODULES"
# General Modules
import time
import datetime as dt
import sys, os, shutil, re, string
#import matplotlib.pyplot as mpl
import numpy as np
# Keithley Modules
import visa
# MayaLSL Modules
import seabreeze.spectrometers as sb
# ThorLab Modules
import thorlabs_apt as apt
# GUI Modules
import Tkinter as tk
import ttk as ttk
import ScrolledText as tkst
#import tkMessageBox as tkmb
import matplotlib.pyplot as mpl
import matplotlib.figure as mplfig
import matplotlib.backends.backend_tkagg as tkagg
import threading
import Queue

"HARDWARE SETUP"
# ThorLabs plugs into port directly
# OceanOptics and Keithley plug into port via USB adapter
# Delete the counter.json file before the first run after plugging in MayaLSL
# Restart kernal if ThorLab Motor is misbehaving
# Home motor manually
# Look at how far away the motor is from home, may need to increase homing time if far from 0

"TROUBLESHOOTING" # IN THIS ORDER! 
# 1. RESTARTING THE KERNAL
# 2. DELETING THE COUNTER 
# 3. UNPLUGGING AND REPLUGGING HARDWARE
# 4. CLOSING AND REOPENING THIS FILE 

"ALWAYS QUIT THE GUI WINDOW BEFORE RESTARTING KERNAL OR CLOSING PYTHON"
"OTHERWISE THE DLL FOR THE MOTOR CAN'T BE LOADED WITHOUT CAUSING A FATAL ERROR"
param = {}
for x in range(0,18):
    param[x] = ''
running = False

# Loads spectrometer and motor devices
class DEVICES:
    # ThorLabs Finding Device
    THORLAB_devices = apt.list_available_devices()
    PLmotor = apt.Motor(55000032)
    ELmotor = apt.Motor(55001039)
    PLmotor.set_velocity_parameters(0,9,5) # velocity MUST be set to avoid the motor moving slowly
    PLmotor.set_hardware_limit_switches(5,5) # ensures that the motor homes properly - home in reverse with reverse lim switches
    PLmotor.set_move_home_parameters(2,1,9,3)
    ELmotor.set_velocity_parameters(0,9,5) # velocity MUST be set to avoid the motor moving slowly
    ELmotor.set_hardware_limit_switches(5,5) # ensures that the motor homes properly - home in reverse with reverse lim switches
    ELmotor.set_move_home_parameters(2,1,9,3)    
    # MayaLSL Finding Device    
    MAYA_devices = sb.list_devices()
    spec = sb.Spectrometer(MAYA_devices[0]) # initialise the spectrometer
    try:
        spec = sb.Spectrometer(MAYA_devices[0]) # initialise the spectrometer
    except:
        pass

"#####################################################################"
"###############################GUI CODE##############################"
"#####################################################################"

# There can't be any measurement processing here
# This is code purely to control the GUI
class GUI:       

    "SETTING UP MAIN WINDOW"
    def __init__(self,windowtitle):
        self.root = tk.Tk()
        self.root.title(windowtitle)
        self.root.geometry('1124x560')      
        self.notebook = ttk.Notebook(self.root)
        
        "CONFIGURING LAYOUT AND PARAMETERS"  
        self.printcount = 0 
        self.graphcount = 0
        self.prints = {}        
        self.graphs = {}
        for x in range(0,16,1):
            self.root.grid_rowconfigure(x, minsize=10, weight=1)
        for x in range(0,16,1):    
            self.root.grid_columnconfigure(x, minsize=10, weight=1)
    
    "ADDING TABS AND WIDGETS"
    def add_tab(self,title,widgets):   
        
        "WRITING THE MAIN GUI INTERFACE"
        tab = ttk.Frame(self.notebook) 
        self.notebook.add(tab, text=title)   # Creating a tab and adding it to the GUI
        
        # Creating a pane for each widget
        pane0 = ttk.LabelFrame(tab)
        pane0.grid(column=1, row=2, columnspan=6, sticky="nsew")
        param_text0 = tk.Label(pane0, text="Sample name") 
        param_text0.grid(column=1, row=2, sticky="ew", pady=2, padx=5) 
        param0 = tk.Entry(pane0) 
        param0.grid(column=2, row=2, sticky="ew", pady=2, padx=5) 
        def enter_param0():
            param[0] = param0.get()
            entered = 'Sample name  :  ' + param[0]
            param_text0.configure(text=entered) 
            param0.delete(0, 'end')               
        button0 = tk.Button(pane0, text="Enter", command=enter_param0) 
        button0.grid(column=3, row=2, sticky="ew", pady=2, padx=5) #widget0 = [param_text0,param0,button0]       
        pane1 = ttk.LabelFrame(tab)
        pane1.grid(column=1, row=3, columnspan=6, rowspan=3, sticky="nsew")
        pane2 = ttk.LabelFrame(tab)
        pane2.grid(column=1, row=6, columnspan=6, sticky="nsew")
        pane3 = ttk.LabelFrame(tab)
        pane3.grid(column=1, row=7, columnspan=6, rowspan=4, sticky="nsew")
        pane4 = ttk.LabelFrame(tab)
        pane4.grid(column=1, row=11, columnspan=6, rowspan=3, sticky="nsew") 
        pane5 = ttk.LabelFrame(tab)
        pane5.grid(column=9, row=9, columnspan=6, rowspan=7, sticky="nsew")           

        # Padding between input and output widgets
        padding_text1 = tk.Label(tab, text="  ") 
        padding_text1.grid(column=0, row=2, rowspan=16, padx=5) 
        padding_text2 = tk.Label(tab, text="  ") 
        padding_text2.grid(column=7, row=2, rowspan=16, padx=5) 
        padding_text3 = tk.Label(tab, text="  ") 
        padding_text3.grid(column=8, row=2, rowspan=16, padx=5) 
        padding_text4 = tk.Label(tab, text="  ") 
        padding_text4.grid(column=15, row=2, rowspan=16, padx=5)
        
        if title == 'EL Measurement':   # Setting titles and headings         
            self.label = ttk.Label(tab,text="Here you can control the electroluminescence measurement of an OLED.")
            self.label.grid(column=1,row=0,columnspan=14,pady=2,sticky="ew")
            self.label = ttk.Label(tab,text="All units are SI and program will use default parameters if unspecified.")
            self.label.grid(column=1,row=1,columnspan=14,pady=2,sticky="ew")
            self.notebook.pack(fill="both", expand=True)
            self.title = title 
            # Tab specific output widgets specified here
            self.paneEL = ttk.LabelFrame(tab)
            self.paneEL.grid(column=9, row=2, columnspan=6, rowspan=7, sticky="nsew")
            self.padding_textEL = tk.Label(self.paneEL, text="      ") 
            self.padding_textEL.grid(column=9, row=2, sticky="nsew") 
            self.scrolling_textEL = tkst.ScrolledText(pane5,wrap=tk.WORD,width=50,height=5)
            self.scrolling_textEL.grid(column=9, row=9, columnspan=6, rowspan=7, sticky="nsew")
            self.scrolling_textEL.insert(tk.INSERT,"Output from the measurement: ")
            # Tab specific measurement button specified here
            self.button_paneEL = ttk.LabelFrame(tab)
            self.button_paneEL.grid(column=1, row=14, columnspan=6, sticky="nsew") 
            self.start_buttonEL = tk.Button(self.button_paneEL, text="Run Measurement", command=self.start) 
            self.start_buttonEL.grid(column=6, row=14, sticky="nsew", padx=10)               

        
        if title == 'PL Measurement': # Setting titles and headings 
            self.label = ttk.Label(tab,text="Here you can control the photoluminescence measurement of a thin film.")
            self.label.grid(column=1,row=0,columnspan=14,pady=2,sticky="ew")
            self.label = ttk.Label(tab,text="All units are SI and program will use default parameters if unspecified.")
            self.label.grid(column=1,row=1,columnspan=14,pady=2,sticky="ew")
            self.notebook.pack(fill="both", expand=True)
            self.title = title 
            # Tab specific output widgets specified here            
            self.panePL = ttk.LabelFrame(tab)
            self.panePL.grid(column=9, row=2, columnspan=6, rowspan=7, sticky="nsew")
            self.padding_textPL = tk.Label(self.panePL, text="      ") 
            self.padding_textPL.grid(column=9, row=2, sticky="nsew") 
            self.scrolling_textPL = tkst.ScrolledText(pane5,wrap=tk.WORD,width=50,height=5)
            self.scrolling_textPL.grid(column=9, row=9, columnspan=6, rowspan=7, sticky="nsew")
            self.scrolling_textPL.insert(tk.INSERT,"Output from the measurement: ")
            # Tab specific measurement button specified here
            self.button_panePL = ttk.LabelFrame(tab)
            self.button_panePL.grid(column=1, row=14, columnspan=6, sticky="nsew") 
            self.start_buttonPL = tk.Button(self.button_panePL, text="Run Measurement", command=self.start) 
            self.start_buttonPL.grid(column=6, row=14, sticky="nsew", padx=10)               

        for widget in widgets:           
           
            if widget == 1:                
                param_text1 = tk.Label(pane1, text="Offset angle") 
                param_text1.grid(column=1, row=3, sticky="ew", pady=2) 
                param1 = tk.Entry(pane1) 
                param1.grid(column=2, row=3, sticky="ew", padx=5)
                def enter_param1():
                    param[1] = param1.get()
                    entered = 'Offset angle  :  ' + param[1]
                    param_text1.configure(text=entered) 
                    current_tab = gui.notebook.tab(gui.notebook.select(),"text")
                    if current_tab == 'EL Measurement':
                        DEVICES.ELmotor.move_to(float(param[1])+90)
                    elif current_tab == 'PL Measurement':
                        DEVICES.PLmotor.move_to(float(param[1])+90)
                    param1.delete(0, 'end') 
                button1 = tk.Button(pane1, text="Enter", command=enter_param1) 
                button1.grid(column=3, row=3, sticky="ew", padx=5) 
                #widget1 = [param_text1,param1,button1]
                
                param_text2 = tk.Label(pane1, text="Step angle") 
                param_text2.grid(column=1, row=4, sticky="ew", pady=2) 
                param2 = tk.Entry(pane1) 
                param2.grid(column=2, row=4, sticky="ew", padx=10)
                def enter_param2():
                    param[2] = param2.get()
                    entered = 'Step angle  :  ' + param[2]
                    param_text2.configure(text=entered)  
                    param2.delete(0, 'end') 
                button2 = tk.Button(pane1, text="Enter", command=enter_param2) 
                button2.grid(column=3, row=4, sticky="ew", padx=5) 
                #widget2 = [param_text2,param2,button2]
                
                param_text3 = tk.Label(pane1, text="Integration time") 
                param_text3.grid(column=1, row=5, sticky="ew", pady=2) 
                param3 = tk.Entry(pane1) 
                param3.grid(column=2, row=5, sticky="ew", padx=5) 
                def enter_param3(): 
                    param[3] = param3.get()
                    entered = 'Integration time  :  ' + param[3]
                    param_text3.configure(text=entered) 
                    param3.delete(0, 'end') 
                button3 = tk.Button(pane1, text="Enter", command=enter_param3) 
                button3.grid(column=3, row=5, sticky="ew", padx=5)
                #widget3 = [param_text3,param3,button3]
                
                param_text4 = tk.Label(pane1, text="Homing time") 
                param_text4.grid(column=4, row=3, sticky="ew", pady=2) 
                param4 = tk.Entry(pane1) 
                param4.grid(column=5, row=3, sticky="ew", padx=5)
                def enter_param4():                   
                    param[4] = param4.get()
                    entered = 'Homing time  :  ' + param[4] 
                    param_text4.configure(text=entered)  
                    param4.delete(0, 'end') 
                button4 = tk.Button(pane1, text="Enter", command=enter_param4) 
                button4.grid(column=6, row=3, sticky="ew", padx=5) 
                #widget4 = [param_text4,param4,button4]
                
                param_text5 = tk.Label(pane1, text="Moving time") 
                param_text5.grid(column=4, row=4, sticky="ew", pady=2) 
                param5 = tk.Entry(pane1) 
                param5.grid(column=5, row=4, sticky="ew", padx=5)
                def enter_param5(): 
                    param[5] = param5.get()
                    entered = 'Moving time  :  ' + param[5]  
                    param_text5.configure(text=entered)
                    param5.delete(0, 'end') 
                button5 = tk.Button(pane1, text="Enter", command=enter_param5) 
                button5.grid(column=6, row=4, sticky="ew", padx=5) 
                #widget5 = [param_text5,param5,button5]
                
                param_text6 = tk.Label(pane1, text="Pulse duration") 
                param_text6.grid(column=4, row=5, sticky="ew", pady=2) 
                param6 = tk.Entry(pane1) 
                param6.grid(column=5, row=5, sticky="ew", padx=5)
                def enter_param6():
                    param[6] = param6.get() 
                    entered = 'Pulse duration  :  ' + param[6]
                    param_text6.configure(text=entered) 
                    param6.delete(0, 'end') 
                button6 = tk.Button(pane1, text="Enter", command=enter_param6) 
                button6.grid(column=6, row=5, sticky="ew", padx=5) 
                #widget6 = [param_text6,param6,button6]
            
            if widget == 2:
                def command1():
                    param[7] = 'F'
                    
                def command2():
                    param[7] = 'HL'
                    
                def command3():
                    param[7] = 'HR'            
                 
                var1 = tk.IntVar()
                var1.set(1)
                rad1 = tk.Radiobutton(pane2, text='Full 180 (Default for EL)', variable=var1, value=1, command=command1,indicatoron=0) 
                rad2 = tk.Radiobutton(pane2, text='Half 90 LHS (Default for PL)', variable=var1, value=2, command=command2,indicatoron=0)                 
                rad3 = tk.Radiobutton(pane2, text='Half 90 RHS', variable=var1, value=3,command=command3,indicatoron=0)                 
                rad1.grid(column=1, row=6, sticky="nsew", padx=5)                  
                rad2.grid(column=2, row=6, sticky="nsew", padx=5)                  
                rad3.grid(column=3, row=6, sticky="nsew", padx=5)    
                #widget6 = [rad1,rad2,rad3]
                    
            if widget == 3: 
                param[8] = 'N'
                var2 = tk.BooleanVar()
                var2.set(False)
                
                widget3 = {}
                param_text9 = tk.Label(pane3, text="Min voltage") 
                param_text9.grid(column=1, row=7, sticky="ew", pady=2) 
                param9 = tk.Entry(pane3) 
                param9.grid(column=2, row=7, sticky="ew", padx=5)  
                def enter_param9(): 
                    param[9]  = param9.get()
                    entered = 'Min voltage  :  ' + param[9]  
                    param_text9.configure(text=entered) 
                    param9.delete(0, 'end') 
                button9 = tk.Button(pane3, text="Enter", command=enter_param9) 
                button9.grid(column=3, row=7, sticky="ew", padx=5)
                widget3[1] = [param_text9,param9,button9]
                
                param_text10 = tk.Label(pane3, text="Change voltage") 
                param_text10.grid(column=1, row=8, sticky="ew", pady=2) 
                param10 = tk.Entry(pane3) 
                param10.grid(column=2, row=8, sticky="ew", padx=5)
                def enter_param10(): 
                    param[10] = param10.get()
                    entered = 'Changeover voltage  :  ' + param[10] 
                    param_text10.configure(text=entered)      
                    param10.delete(0, 'end') 
                button10 = tk.Button(pane3, text="Enter", command=enter_param10) 
                button10.grid(column=3, row=8, sticky="ew", padx=5)
                widget3[2] = [param_text10,param10,button10]
                
                param_text11 = tk.Label(pane3, text="Max voltage") 
                param_text11.grid(column=1, row=9, sticky="ew", pady=2) 
                param11 = tk.Entry(pane3) 
                param11.grid(column=2, row=9, sticky="ew", padx=5)
                def enter_param11(): 
                    param[11] = param11.get()
                    entered = 'Max voltage :  ' + param[11] 
                    param_text11.configure(text=entered)  
                    param11.delete(0, 'end') 
                button11 = tk.Button(pane3, text="Enter", command=enter_param11) 
                button11.grid(column=3, row=9, sticky="ew", padx=5)
                widget3[3] = [param_text11,param11,button11]
                
                param_text12 = tk.Label(pane3, text="Step voltage at low voltages") 
                param_text12.grid(column=4, row=7, sticky="ew", pady=2) 
                param12 = tk.Entry(pane3) 
                param12.grid(column=5, row=7, sticky="ew", padx=5) 
                def enter_param12(): 
                    param[12] = param12.get()
                    entered = 'Step voltage at low voltages  :  ' + param[12]
                    param_text12.configure(text=entered) 
                    param12.delete(0, 'end') 
                button12 = tk.Button(pane3, text="Enter", command=enter_param12) 
                button12.grid(column=6, row=7, sticky="ew", padx=5) 
                widget3[4] = [param_text12,param12,button12]
                
                param_text13 = tk.Label(pane3, text="Step voltage at high voltages") 
                param_text13.grid(column=4, row=8, sticky="ew", pady=2) 
                param13 = tk.Entry(pane3) 
                param13.grid(column=5, row=8, sticky="ew", padx=5) 
                def enter_param13(): 
                    param[13] = param13.get()
                    entered = 'Step voltage at high voltages  :  ' + param[13]
                    param_text13.configure(text=entered) 
                    param13.delete(0, 'end') 
                button13 = tk.Button(pane3, text="Enter", command=enter_param13) 
                button13.grid(column=6, row=8, sticky="ew", padx=5) 
                widget3[5] = [param_text13,param13,button13]
                
                param_text14 = tk.Label(pane3, text="Scan compliance") 
                param_text14.grid(column=4, row=9, sticky="ew", pady=2) 
                param14 = tk.Entry(pane3) 
                param14.grid(column=5, row=9, sticky="ew", padx=5) 
                def enter_param14():    
                    param[14] = param14.get()
                    entered = 'Scan compliance  :  ' + param[14]
                    param_text14.configure(text=entered) 
                    param14.delete(0, 'end') 
                button14 = tk.Button(pane3, text="Enter", command=enter_param14) 
                button14.grid(column=6, row=9, sticky="ew", padx=5)  
                widget3[6] = [param_text14,param14,button14]
                
                if var2.get() == True:
                    for x in range(1,7):
                        for entry in widget3[x]:
                            entry.configure(state="normal")
                
                if var2.get() == False:                    
                    for x in range(1,7):
                                for entry in widget3[x]:
                                    entry.configure(state="disabled")  

                def show_scan_opt():                   
                    if var2.get() == True:                        
                        param[8] = 'Y' # scan_status
                        for x in range(1,7):
                            for entry in widget3[x]:
                                entry.configure(state="normal")                
                    else: 
                        param[8] = 'N'
                        for x in range(1,7):
                            for entry in widget3[x]:
                                entry.configure(state="disabled")                        
                            
                var2 = tk.BooleanVar()
                var2.set(False)
                scan = tk.Checkbutton(pane3, text='Take voltage scan?', variable=var2, command=show_scan_opt)
                scan.grid(column=5, row=10)  
            
            if widget == 4:
                param_text15a = tk.Label(pane4, text="Source") 
                param_text15a.grid(column=1, row=11, sticky="ew", padx=5) 
                param_text15b = tk.Label(pane4, text="Sense") 
                param_text15b.grid(column=3, row=11, sticky="ew", padx=5) 
                               
                def command15a():
                    # Selecting current source
                    param_text15a.configure(state="normal")
                    param_text15b.configure(state="disabled")
                    param_text16a.grid(column=7, row=12, sticky="E", padx=5)  
                    param_text16b.grid_forget()
                    param_text17a.grid_forget()
                    param_text17b.grid(column=7, row=13, sticky="E", padx=5) 
                    param[15] = 'Current'                   
                    
                def command15b():
                    # Selecting voltage source
                    param_text15a.configure(state="disabled")
                    param_text15b.configure(state="normal")
                    param_text16a.grid_forget()
                    param_text16b.grid(column=7, row=12, sticky="W", padx=5) 
                    param_text17a.grid(column=7, row=13, sticky="W", padx=5)  
                    param_text17b.grid_forget()
                    param[15] = 'Volt'
                    
                    
                def enter_param16(): 
                    param[16] = self.param16.get()
                    entered = 'Source value  :  ' + param[16] 
                    param_text16.configure(text=entered) 
                    param16.delete(0, 'end') 
                    
                def enter_param17(): 
                    param[17] = self.param17.get()
                    entered = 'Compliance  :  ' + param[17] 
                    param_text17.configure(text=entered) 
                    param17.delete(0, 'end') 
                             
                var3 = tk.IntVar()
                var3.set(1)
                rad1 = tk.Radiobutton(pane4, text='Current', variable=var3, value=1, command=command15a,indicatoron=0) 
                rad2 = tk.Radiobutton(pane4, text='Voltage', variable=var3, value=2, command=command15b,indicatoron=0)                                  
                rad1.grid(column=1, row=12, padx=10, sticky="nsew")                  
                rad2.grid(column=1, row=13, padx=10, sticky="nsew") 
                param_text15a = tk.Label(pane4, text='Voltage') 
                param_text15a.grid(column=3, row=12, sticky="ew", padx=5) 
                param_text15b = tk.Label(pane4, text='Current') 
                param_text15b.grid(column=3, row=13, sticky="ew", padx=5) 
                
                param_text16 = tk.Label(pane4, text="Source value") 
                param_text16.grid(column=5, row=12, sticky="ew", padx=5) 
                param16 = tk.Entry(pane4) 
                param16.grid(column=6, row=12)
                param_text16a = tk.Label(pane4, text="A") 
                param_text16a.grid(column=7, row=12, sticky="ew", padx=5) 
                param_text16b = tk.Label(pane4, text="V") 
                param_text16b.grid(column=7, row=12, sticky="ew", padx=10)
                button16 = tk.Button(pane4, text="Enter", command=enter_param16) 
                button16.grid(column=8, row=12, sticky="ew", padx=10) 
                
                param_text17 = tk.Label(pane4, text="Compliance") 
                param_text17.grid(column=5, row=13, sticky="ew", padx=10) 
                param17 = tk.Entry(pane4) 
                param17.grid(column=6, row=13)
                param_text17a = tk.Label(pane4, text="A") 
                param_text17a.grid(column=7, row=13, sticky="ew", padx=10) 
                param_text17b = tk.Label(pane4, text="V") 
                param_text17b.grid(column=7, row=13, sticky="ew", padx=10) 
                button17 = tk.Button(pane4, text="Enter", command=enter_param17) 
                button17.grid(column=8, row=13, sticky="ew", padx=10) 
                
                param_text15a.configure(state="normal")
                param_text15b.configure(state="disabled")
                param_text16a.grid(column=7, row=12, sticky="E", padx=10)  
                param_text16b.grid_forget()
                param_text17a.grid_forget()
                param_text17b.grid(column=7, row=13, sticky="E", padx=10)  
                
    "FUNCTION TO CHECK FOR OUTPUT FROM MEASUREMENT AND DISPLAY IN GUI"
    def check_queue(self):               
        current_tab = gui.notebook.tab(gui.notebook.select(),"text")
        try: 
            output = self.queue.get(0)
            if isinstance(output,str): 
                if current_tab == 'EL Measurement':
                    self.scrolling_textEL.insert(tk.INSERT,'\n'+output)
                    self.scrolling_textEL.see('end')
                elif current_tab == 'PL Measurement':
                    self.scrolling_textPL.insert(tk.INSERT,'\n'+output)
                    self.scrolling_textPL.see('end')
                self.root.after(1000,self.check_queue)                
                print output                
            else: 
                fig = mplfig.Figure()
                a = fig.add_subplot(111)
                a.plot(output[0],output[1])
                a.set_title ("Spectrum", fontsize=16)
                a.set_xlabel("Wavelength", fontsize=14)
                a.set_ylabel("Intensity", fontsize=14)                
                if current_tab == 'EL Measurement':
                    if self.graphcount == 0:
                        self.padding_textEL.destroy()
                    self.graphs[self.graphcount] = tkagg.FigureCanvasTkAgg(fig, master=self.paneEL)
                elif current_tab == 'PL Measurement':
                    if self.graphcount == 0:
                        self.padding_textPL.destroy()
                    self.graphs[self.graphcount] = tkagg.FigureCanvasTkAgg(fig, master=self.panePL)                    
                if self.graphcount > 0:
                    self.graphs[self.graphcount-1].get_tk_widget().destroy()  
                self.graphs[self.graphcount].get_tk_widget().grid(column=10, row=2, columnspan=5, rowspan=3)
                self.graphs[self.graphcount].draw() 
                mpl.plot(output[0],output[1])
                mpl.show()  
                self.graphcount+=1 
                self.root.after(1000,self.check_queue)                
        except Queue.Empty:
            self.root.after(1000,self.check_queue)
    
    "FUNCTION TO START MEASUREMENT THREAD AND CHANGE MEASURING BUTTON TO CANCEL"    
    def start(self):
        global running
        running = True
        self.queue = Queue.Queue()
        current_tab = gui.notebook.tab(gui.notebook.select(),"text")
        if current_tab == 'EL Measurement':
            ELTASK(self.queue).start()
            self.start_buttonEL.destroy()
            self.stop_buttonEL = tk.Button(self.button_paneEL, text="Stop Measurement", command=self.stop) 
            self.stop_buttonEL.grid(column=6, row=14, sticky="nsew", padx=10)               
        elif current_tab == 'PL Measurement':
            PLTASK(self.queue).start()   
            self.start_buttonPL.destroy()
            self.stop_buttonPL = tk.Button(self.button_panePL, text="Stop Measurement", command=self.stop) 
            self.stop_buttonPL.grid(column=6, row=14, sticky="nsew", padx=10)              
        self.root.after(1000,self.check_queue)  

            
    def stop(self):
        global running
        running = False
        current_tab = gui.notebook.tab(gui.notebook.select(),"text")
        if current_tab == 'EL Measurement':            
            self.stop_buttonEL.destroy()
            self.start_buttonEL = tk.Button(self.button_paneEL, text="Run Measurement", command=self.start) 
            self.start_buttonEL.grid(column=6, row=14, sticky="nsew", padx=10)               
        elif current_tab == 'PL Measurement':
            self.stop_buttonPL.destroy()
            self.start_buttonPL = tk.Button(self.button_panePL, text="Run Measurement", command=self.start) 
            self.start_buttonPL.grid(column=6, row=14, sticky="nsew", padx=10)  
        
    "FUNCTION TO RUN MAIN GUI THREAD"    
    def run(self): 
        self.root.mainloop()
        
    "#####################################################################"
    "##########################MEASUREMENT CODE###########################"
    "#####################################################################" 
    
class ELTASK(threading.Thread):
    
    def __init__(self,queue):
        threading.Thread.__init__(self,target=self.testrunEL)
        self.queue = queue
        
    def testrunEL(self):          
        while running == True:  

            "INITIALIZING SETTINGS"          
            defaults = {}
            settings = {}
            parameters = []  
            "SETTING DEFAULT PARAMETERS"
            defaults[0] = 'test' # sample
            defaults[1] = 318 # offset_angle
            defaults[2] = 1  # step_angle
            defaults[3] = 300000 # integrationtime in microseconds
            defaults[4] = 20.0 # homing_time
            defaults[5] = 0.2 # moving_time
            defaults[6] = 0.2  # pulse_duration in s
            defaults[7] = 'F' # ang_range
            defaults[8] = 'N' # scan_status                
            defaults[9] = -2.0  # min_voltage
            defaults[10] = 2.0 # change_voltage
            defaults[11] = 4.0  # max_voltage
            defaults[12] = 0.1 # min_step_voltage 
            defaults[13] = 1.0 # max_step_voltage 
            defaults[14] = 0.10  # scan_compliance
            defaults[15] = 'Current'  # source 
            defaults[16] = 0.001 # goniometer_value in A for current
            defaults[17] = 5 # goniometer_compliance in V for voltage
            
            "GETTING PARAMETERS FROM GUI, IF BLANK SETTING AS DEFAULT"                
            for x in range(0,18,1):                        
                if not param[x]:
                    parameters.append(defaults[x])
                else:
                    settings[x] = param[x]
                    parameters.append(settings[x])
            if parameters[7] == 'F':
                self.min_angle = float(parameters[1]) - 90
                self.max_angle = float(parameters[1]) + 90
            elif parameters[7] == 'HL':
                self.min_angle = float(parameters[1])
                self.max_angle = float(parameters[1]) + 90
            elif parameters[7] == 'HR':
                self.min_angle = float(parameters[1]) - 90
                self.max_angle = float(parameters[1])
            else:
                self.queue.put('Invalid input.')
            
            "SETTING PARAMTERS"
            self.sample = parameters[0]
            self.offset_angle = float(parameters[1])
            self.step_angle = float(parameters[2])
            self.integrationtime = float(parameters[3])
            self.homing_time = float(parameters[4])
            self.moving_time = float(parameters[5])
            self.pulse_duration = float(parameters[6])
            self.ang_range = parameters[7]
            self.scan_status = parameters[8]
            self.min_voltage = float(parameters[9]) 
            self.change_voltage = float(parameters[10])
            self.max_voltage = float(parameters[11])
            self.min_step_voltage = float(parameters[12]) 
            self.max_step_voltage = float(parameters[13]) 
            self.scan_compliance = float(parameters[14]) 
            self.source = parameters[15] 
            self.goniometer_value  = float(parameters[16]) 
            self.goniometer_compliance = float(parameters[17])
            
            "SETTING DIRECTORY DETAILS"
            now = dt.datetime.now()
            datetime = str(now.strftime("%Y-%m-%d %H:%M").replace(" ","").replace(":","").replace("-",""))
            self.queue.put('Measurement code : ' + self.sample + datetime + '  (OLED device code followed by the datetime of measurement).')
            # Set directories for recorded data.
            directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', self.sample, datetime, 'raw')) # Folder to separate raw and processed data
            if os.path.isdir(directory):
                pass
            else:
                os.makedirs(directory)
                
            "SETTING FILE DETAILS"
            # Filename Parameters
            keithleyfilepath = os.path.join(directory, 'keithleydata')
            mayafilepath = os.path.join(directory, 'spectrumdata')
            if os.path.isdir(keithleyfilepath):
                pass
            else:
                os.makedirs(keithleyfilepath)
            if os.path.isdir(mayafilepath):
                pass
            else:
                os.makedirs(mayafilepath)
            
            keithleyfilename = 'keithleyPDvoltages.txt'  # for filenames have foldername and filename
            keithleyfilename = os.path.abspath(os.path.join(keithleyfilepath, keithleyfilename)) # amended with full path
            
            # Header Parameters
            line01 = 'Measurement code : ' + self.sample + datetime
            line02 = 'Measurement programme :	"GatherLab Goniometer Measurement System".py'
            linex = 'Credits :	Gather Lab, University of St Andrews, 2018'
            linexx = 'Integration Time:  ' + str(self.integrationtime) + 'micro s'
            line03 = 'Pulse duration :		' + str(self.pulse_duration) + ' s'
            line04 = 'Step time between voltages :		' + str(self.moving_time) + ' s'
            if self.source == 'Current':
            	line05 = 'Source Current:		' + str(self.goniometer_value * 1e3) + ' mA'
            	line06 = 'Voltage Compliance:	' + str(self.goniometer_compliance) + ' V'
            else:
            	line05 = 'Source Voltage:		' + str(self.goniometer_value) + ' V'
            	line06 = 'Current Compliance:	' + str(self.goniometer_compliance * 1e3) + ' mA'	
            line07 = '### Measurement data ###'
            line08 = 'OLEDVoltage	OLEDCurrent Photodiode Voltage'
            line09 = 'V	              mA               V'
            line10 = 'Angle    OLEDVoltage   	OLEDCurrent'
            line11 = 'Degrees 	  V       	 A'
            line12 = 'Wavelength   Intensity'
            line13 = 'nm             -'
            
            header_lines = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line08, line09] # PD Voltages
            header_lines2 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line10, line11] # OLED Voltages
            header_lines3 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line12, line13] # Spectrum Data
                       
            "INITIALIZING HARDWARE"
            # Keithley Finding Device
            rm = visa.ResourceManager()
            keith = rm.open_resource(u'USB0::0x05E6::0x2450::04102170::INSTR')
            keithmulti = rm.open_resource(u'USB0::0x05E6::0x2100::8003430::INSTR')
            self.queue.put('\nKeithley Multimeter : '+ str(keithmulti.query('*IDN?')))
            self.queue.put('\nKeithley Sourcemeter : '+ str(keith.query('*IDN?')))
            
            self.queue.put('\nOceanOptics : '+ str(DEVICES.MAYA_devices[0]))
            DEVICES.spec.integration_time_micros(self.integrationtime) 
    
            # Write operational parameters to Sourcemeter (Voltage to OLED)
            keith.write('*rst')  # reset instrument
            keith.write('Source:Function Volt')  # set voltage as source
            keith.write('Sense:Function "Current"')  # choose current for measuring
            keith.write('Source:Volt:ILimit ' + str(self.scan_compliance))  # set compliance
            keith.write('Source:Volt:READ:BACK ON')  # reads back the set voltage
            keith.write('Current:NPLCycles 1')  # sets the read-out speed and accuracy (0.01 fastest, 10 slowest but highest accuracy)
            keith.write('Current:AZero OFF')  # turn off autozero
            keith.write('Source:Volt:Delay:AUTO OFF')  # turn off autodelay
            
            # Write operational parameters to Multimeter (Voltage from Photodiode)
            keithmulti.write('*rst')  # reset instrument
            keithmulti.write('SENSe:VOLTage:DC:RANGe 10')  # sets the voltage range
            keithmulti.query('VOLTage:DC:RESolution?')  # sets the voltage resolution
            keithmulti.write('VOLTage:NPLCycles 1')  # sets the read-out speed and accuracy (0.01 fastest, 10 slowest but highest accuracy)
            keithmulti.write('TRIGer:SOURce BUS')  # sets the trigger to activate immediately after 'idle' -> 'wait-for-trigger' 
            keithmulti.write('TRIGer:DELay 0')  # sets the trigger to activate immediately after 'idle' -> 'wait-for-trigger' 
            
            "MOVING TO INITIAL POSITION"       
            DEVICES.ELmotor.move_to(self.max_angle) 
            time.sleep(self.homing_time)
                         
            "#####################################################################"
            "#####TAKING MEASUREMENTS FROM THE THORLABS PDA100A2 PHOTODIODE#####"
            "#####################################################################"
            
            self.queue.put("\n\nPHOTODIODE READINGS") 
            "IMPLEMENTATION"                               
            # generate empty lists for later data collection
            low_vlt = np.arange(self.min_voltage, self.change_voltage, self.max_step_voltage) # Voltage points for low OLED voltage
            high_vlt = np.arange(self.change_voltage, self.max_voltage+0.1, self.min_step_voltage) # Voltage points for high OLED voltage
            OLEDvlt = []
            OLEDcrt = []
            PDvlt = []
            "SCANNING VOLTAGES"     
            # Optional scanning voltage readings, runs readings if Y, anything else and this section is skipped
            if self.scan_status == str('Y'):  
                
                keithmulti.write("INITiate") # Initiating 'wait_for_trigger' mode for Multimeter
                keith.write('Trace:Make "OLEDbuffer", ' + str(max(len(low_vlt)+len(high_vlt), 10))) # Buffer for Sourcemeter
                keith.write('Trace:Clear "OLEDbuffer"')  # Keithley empties the buffer
                background_diodevoltage = float(keithmulti.query('MEASure:VOLTage:DC?')) # Take PD voltage reading from Multimeter for background
                self.queue.put("Background Photodiode Voltage :"+ str(background_diodevoltage) + ' V')
                self.queue.put('\nSaving output to: ' + 'keithleyPDvoltages.txt')
                keith.write('Output ON')    
                # Low Voltage Readings
                for voltage in low_vlt:
                    self.queue.put("\nOLED Voltage : "+ str(voltage) + ' V')
                    keith.write('Source:Volt ' + str(voltage))  # Set voltage to source_value
                    
                    diodevoltage = float(keithmulti.query('MEASure:VOLTage:DC?')) # Take PD voltage reading from Multimeter
                    oledcurrent = float(keith.query('Read? "OLEDbuffer"')[:-1]) # Take OLED current reading from Sourcemeter
                    self.queue.put("OLED Current : "+ str(oledcurrent*1e3) + ' mA')
                    self.queue.put("Photodiode Voltage :"+ str(diodevoltage - background_diodevoltage) + ' V')
                    PDvlt.append(diodevoltage - background_diodevoltage)
                    OLEDcrt.append(oledcurrent)
                    OLEDvlt.append(voltage)   
                    
                # High Voltage Readings
                for voltage in high_vlt:
                    self.queue.put("\nOLED Voltage : "+ str(voltage) + ' V')
                    keith.write('Source:Volt ' + str(voltage))  # Set voltage to source_value
                    
                    diodevoltage = float(keithmulti.query('MEASure:VOLTage:DC?')) # Take PD voltage reading from Multimeter
                    oledcurrent = float(keith.query('Read? "OLEDbuffer"')[:-1]) # Take OLED current reading from Sourcemeter
                    self.queue.put("OLED Current : "+ str(oledcurrent*1e3) + ' mA')
                    self.queue.put("Photodiode Voltage :"+ str(diodevoltage - background_diodevoltage) + ' V')
                    PDvlt.append(diodevoltage - background_diodevoltage)
                    OLEDcrt.append(oledcurrent)
                    OLEDvlt.append(voltage)   
                    self.scan_status = 'N'   
                        
                keith.write('Output OFF')
                OLEDvolt = np.array(OLEDvlt)  # Creates voltage array
                OLEDcurrent = np.array(OLEDcrt) * 1e3  # Creates current array; NOTE: current in mA !!!
                PDvoltage = np.array(PDvlt)
                photodiodedata = np.stack((OLEDvolt, OLEDcurrent, PDvoltage)) 
                np.savetxt(keithleyfilename, photodiodedata.T, fmt='%.4f %.4e %.6f', header='\n'.join(header_lines), delimiter='\t', comments='')
        
            "SPECIFIC READING AT CERTAIN CURRENT"
            
            # Write operational parameters to Sourcemeter (Current to OLED)
            keith.write('Source:Function Current')  # set current as source
            keith.write('Source:Current ' + str(self.goniometer_value))  # set current to source_value
            keith.write('Sense:Function "Volt"')  # choose voltage for measuring
            keith.write('Source:Current:VLimit ' + str(self.goniometer_compliance))  # set voltage compliance to compliance
            keith.write('Source:Current:READ:BACK OFF')  # record preset source value instead of measuring it anew. NO CURRENT IS MEASURED!!! (Costs approx. 1.5 ms)
            keith.write('Volt:AZero OFF')  # turn off autozero
            keith.write('Source:Current:Delay:AUTO OFF')  # turn off autodelay
            background_diodevoltage = float(keithmulti.query('MEASure:VOLTage:DC?')) # Take PD voltage reading from Multimeter for background
                
            keith.write('Output ON')  # Turn power on
            specificPDvoltage = float(keithmulti.query('MEASure:VOLTage:DC?')) # Take PD voltage reading from Multimeter
            specificPDvoltage = specificPDvoltage - background_diodevoltage # Background Subtracted
            specificOLEDcurrent = float(keith.query('MEASure:CURRent:DC?')) # Take OLED current reading from Sourcemeter
            specificOLEDvoltage = float(keith.query('MEASure:VOLTage:DC?')) # Take OLED current reading from Sourcemeter
            keith.write('Output OFF')  # Turn power off
               
            self.queue.put('\n\nSaving output to: ' + 'specifickeithleyPDvoltages.txt')                 
            self.queue.put("\nPhotodiode Voltage :"+ str(specificPDvoltage) + ' V')
            self.queue.put("OLED Voltage : "+ str(specificOLEDvoltage) + ' V')
            self.queue.put("OLED Current : "+ str(specificOLEDcurrent*1e3) + ' mA')
            
            
            specificphotodiodedata = np.stack((np.array(specificOLEDvoltage), np.array(specificOLEDcurrent), np.array(specificPDvoltage)))
            specifickeithleyfilename = 'specifickeithleyPDvoltages.txt'  # for filenames have foldername and filename
            specifickeithleyfilename = os.path.abspath(os.path.join(keithleyfilepath, specifickeithleyfilename)) # amended with full path
            np.savetxt(specifickeithleyfilename, specificphotodiodedata, fmt='%.4f', header='\n'.join(header_lines), delimiter='\t', comments='')
            
            "#####################################################################"
            "####TAKING MEASUREMENTS FROM THE OCEANOPTICS MAYALSL SPECTROMETER####"
            "#####################################################################"
            
            self.queue.put("\n\nSPECTROMETER READINGS") 
            
            "SETTING PARAMETERS"
            # Keithley OLED Current Parameters
            warning_message = False
            if self.source == 'Current':
            	sense = 'Volt'
            else:
            	sense = 'Current'
            	
            if warning_message is True:
            	self.queue.put("\nWARNING:\n")
            	if self.source == 'Current':
            		self.queue.put("You are about to set " + str(self.source) + " as source with " + str(self.goniometer_value * 1e3) + " mA.")
            		self.queue.put("Your " + sense + " Compliance is " + str (self.goniometer_compliance) + " V.\n")
            	else:
            		self.queue.put("You are about to set " + str(self.source) + " as source with " + str(self.goniometer_value) + " V.")
            		self.queue.put("Your " + sense + " Compliance is " + str (self.goniometer_compliance * 1e3) + " mA.\n")
            	while True:
            		i = input("If this looks right, press Enter to continue. Else press 'q' to quit.")
            		if i == 'q':
            			sys.exit("User exit. Check your operational parameters.")
            		else:
            			break
                    
            # Printing source and compliance
            if self.source == 'Current':
                self.queue.put('\nsource current: ' + str(self.goniometer_value * 1e3) + ' mA')
                self.queue.put('voltage compliance: ' + str(self.goniometer_compliance) + ' V')
            else:
                self.queue.put('\nsource voltage: ' + str(self.goniometer_value) + ' V')
                self.queue.put('current compliance: ' + str(self.goniometer_compliance * 1e3) + ' mA')	
            
            self.queue.put('approx pulse length: ' + str(self.pulse_duration) + ' s')
            self.queue.put('Saving output to: ' + 'keithleyOLEDvoltages.txt' + ' and Angle_.txt'),
            
            # Keithley write operational parameters to SMU
            keith.write('*rst')  # reset instrument        
            if self.source == 'Current':
            	keith.write('Source:Function Current')  # set current as source
            	keith.write('Source:Current ' + str(self.goniometer_value))  # set current to source_value
            	keith.write('Sense:Function "Volt"')  # choose voltage for measuring
            	keith.write('Source:Current:VLimit ' + str(self.goniometer_compliance))  # set voltage compliance to compliance
            	keith.write('Source:Current:READ:BACK OFF')  # record preset source value instead of measuring it anew. NO CURRENT IS MEASURED!!! (Costs approx. 1.5 ms)
            	keith.write('Volt:AZero OFF')  # turn off autozero
            	keith.write('Source:Current:Delay:AUTO OFF')  # turn off autodelay
            else:
                keith.write('Source:Function Volt')  # set voltage as source
                keith.write('Source:Volt ' + str(self.goniometer_value))  # set voltage to source_value
                keith.write('Sense:Function "Current"')  # choose voltage for measuring
                keith.write('Source:Volt:ILimit ' + str(self.goniometer_compliance))  # set voltage
                keith.write('Source:Volt:READ:BACK OFF')  # record preset source value instead of measuring it anew. NO VOLTAGE IS MEASURED!!! (Costs approx. 1.5 ms)
                keith.write('Current:NPLCycles 1')  # set acquisition factor to acq_factor (effectively sets the acquisition time)
                keith.write('Current:AZero OFF')  # turn off autozero
                keith.write('Source:Volt:Delay:AUTO OFF')  # turn off autodelay
            
            self.queue.put('\n\nSource: ' + str(keith.query('Source:Function?')))
            self.queue.put('Sense: ' + str(keith.query('Sense:Voltage:Unit?')))
            
            "SETTING FILE DETAILS"
            # Filename Parameters
            keithleyfilename = 'keithleyOLEDvoltages.txt'  # changing keithley filename
            keithleyfilename = os.path.abspath(os.path.join(keithleyfilepath, keithleyfilename)) # amended with full path
            mayafilename = 'Background.txt' # setting mayalsl filename for dark reading
            mayafilename = os.path.abspath(os.path.join(mayafilepath, mayafilename))
            
            "IMPLEMENTATION"
            # Generate empty lists for current/voltage and wavelength/intensity data collection
            vlt = [] # Voltages
            crt = [] # Currents
            ang = [] # Angles
            wvl = [] # Wavelengths
            inte = [] # Intensities
            spect = [] # Spectrums             
                 
            buffer_length = 1000
            keith.write('Trace:Make "pulsebuffer", ' + str(max(buffer_length, 10)))  # create buffer; buffer size must be between 10 and 11000020
            keith.write('Trace:Clear "pulsebuffer"')  # keithley empties the buffer
            
            DEVICES.ELmotor.move_to(self.min_angle)  
            time.sleep(self.homing_time) 
                
            # Take calibration readings
            spectrum = DEVICES.spec.spectrum() # this gives a pre-stacked array of wavelengths and intensities
            np.savetxt(mayafilename, spectrum.T, fmt='%.4f %.0f', delimiter='\t', header='\n'.join(header_lines3), comments='')
            processing_time = 0.5 # Initial processing time in seconds   
            
            # Move motor by given increment while giving current to OLED and reading spectrum
            for angle in np.arange(self.min_angle, self.max_angle + 1, self.step_angle):           
     
                DEVICES.ELmotor.move_to(angle)  
                time.sleep(self.moving_time)                    
                keith.write('Output ON')
                time.sleep(self.pulse_duration - processing_time)
                start_process = time.clock()
                temp_buffer = float(keith.query('Read? "pulsebuffer"')[:-1]) # take measurement from Keithley
                # Add Keithley readings to lists
                if self.source == 'Current':
                    crt.append(self.goniometer_value)
                    vlt.append(temp_buffer)
                    line13 = 'Source Current:		' + str(self.goniometer_value * 1e3) + ' mA'
                    line14 = 'Source Voltage:      ' + str(temp_buffer) + ' V'
                else:
                    crt.append(temp_buffer)
                    vlt.append(self.goniometer_value)
                    line13 = 'Source Voltage:		' + str(self.goniometer_value) + ' V'
                    line14 = 'Source Current:      ' + str(temp_buffer * 1e3) + ' mA'
                header_lines3.append(line13)
                header_lines3.append(line14)
                # Take spectrometer readings    
                wavelength = DEVICES.spec.wavelengths() # creates a list of wavelengths
                intensity = DEVICES.spec.intensities() # creates a list of intensities
                spectrum = DEVICES.spec.spectrum() # this gives a pre-stacked array of wavelengths and intensities
                wvl.append(wavelength) # adding to a master list (may not be necessary with txt file outputs)
                inte.append(intensity) # adding to a master list (may not be necessary with txt file outputs)
                spect.append(spectrum) # adding to a master list (may not be necessary with txt file outputs)
                
                "DISPLAYING SPECTRUM AS A PLOT"
                self.queue.put([wavelength,intensity])
                
                "SPECTRUM OUTPUT FILE"
                # Angle is written as 0 -> 180 rather than -90 -> 90
                if self.ang_range == 'F':
                    mayafilename = 'Angle'+str(angle + 90 - self.offset_angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                elif self.ang_range == 'HL':
                    mayafilename = 'Angle'+str(angle - self.offset_angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                elif self.ang_range == 'HR':
                    mayafilename = 'Angle'+str(self.offset_angle - angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                mayafilename = os.path.abspath(os.path.join(mayafilepath, mayafilename))
                np.savetxt(mayafilename, spectrum.T, fmt='%.3f %.0f', delimiter='\t', header='\n'.join(header_lines3), comments='')
                keith.write('Output OFF') #Turn current off
                end_process = time.clock()
                processing_time = end_process - start_process
                self.queue.put('\nProcessing time :  '+str(processing_time))
                    
                if self.ang_range == 'F':
                    self.queue.put('\nAngle : '+str(angle + 90 - self.offset_angle))
                    ang.append(angle + 90 - self.offset_angle)
                elif self.ang_range == 'HL':
                    self.queue.put('\nAngle : '+str(angle - self.offset_angle))
                    ang.append(angle - self.offset_angle)
                elif self.ang_range == 'HR':
                    self.queue.put('\nAngle : '+str(self.offset_angle - angle))
                    ang.append(self.offset_angle - angle)
    
            pulse_data = np.stack((ang, vlt, crt))
                            
            "PULSE OUTPUT FILE"
            # Writing the file for Keithley
            if self.source == 'Current':
            	np.savetxt(keithleyfilename, pulse_data.T, fmt='%.0f %.4f %.3e', delimiter='\t', header='\n'.join(header_lines2), comments='')
            else:
            	np.savetxt(keithleyfilename, pulse_data.T, fmt='%.0f %.4f %.3e', delimiter='\t', header='\n'.join(header_lines2), comments='')
                
            self.queue.put('\n\nMEASUREMENT COMPLETE') 
        
class PLTASK(threading.Thread):
    
    def __init__(self,queue):
        threading.Thread.__init__(self,target=self.runPL)
        self.queue = queue
        
    def runPL(self):
        while running == True: 
            "INITIALIZING SETTINGS"          
            defaults = {}
            settings = {}
            parameters = [] 
            
            "SETTING DEFAULT PARAMETERS"
            defaults[0] = 'test' # sample
            defaults[1] = 314 # offset_angle
            defaults[2] = 1  # step_angle
            defaults[3] = 500000 # integrationtime
            defaults[4] = 20.0 # homing_time
            defaults[5] = 0.2 # moving_time
            defaults[6] = 0.2  # pulse_duration
            defaults[7] = 'HL' # ang_range
            
            "GETTING PARAMETERS FROM GUI, IF BLANK SETTING AS DEFAULT"
            for x in range(0,8,1):                        
                if not param[x]:
                    parameters.append(defaults[x])
                else:
                    settings[x] = param[x]
                    parameters.append(settings[x])                
            if parameters[7] == 'F':
                self.min_angle = float(parameters[1]) - 90
                self.max_angle = float(parameters[1]) + 90
            elif parameters[7] == 'HL':
                self.min_angle = float(parameters[1])
                self.max_angle = float(parameters[1]) + 90
            elif parameters[7] == 'HR':
                self.min_angle = float(parameters[1]) - 90
                self.max_angle = float(parameters[1])
            else:
                self.queue.put('Invalid input.')
            
            "SETTING PARAMTERS"
            self.sample = parameters[0]
            self.offset_angle = float(parameters[1])
            self.step_angle = float(parameters[2])
            self.integrationtime = float(parameters[3])
            self.homing_time = float(parameters[4])
            self.moving_time = float(parameters[5])
            self.pulse_duration = float(parameters[6])
            self.ang_range = parameters[7]
            
            "SETTING DIRECTORY DETAILS"
            # Getting date-time
            now = dt.datetime.now()
            datetime = str(now.strftime("%Y-%m-%d %H:%M").replace(" ","").replace(":","").replace("-",""))
            self.queue.put('Measurement code : ' + self.sample + datetime + '  (OLED device code followed by the datetime of measurement).')
            # Set directories for recorded data.
            directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', self.sample, datetime, 'raw')) # Folder to separate raw and processed data
            if os.path.isdir(directory):
                pass
            else:
                os.makedirs(directory)
                
            "SETTING FILE DETAILS"
            # Filename Parameters
            mayafilepath = os.path.join(directory, 'spectrumdata')
            if os.path.isdir(mayafilepath):
                pass
            else:
                os.makedirs(mayafilepath)
                
            mayafilename = 'Background.txt' # Set filename for background reading             
            # Header Parameters
            line01 = 'Measurement code : ' + self.sample + datetime
            line02 = 'Measurement programme :	"GatherLab Goniometer Measurement System".py'
            linex = 'Credits :	GatherLab, University of St Andrews, 2020'
            linexx = 'Integration Time:  ' + str(self.integrationtime) + 'micro s'
            line03 = 'Pulse duration :		' + str(self.pulse_duration) + ' s'
            line04 = 'Step time between voltages :		' + str(self.moving_time) + ' s'
            line05 = 'Offset angle:     ' + str(self.offset_angle)
            line06 = 'Min Angle:  ' + str(0) + 'Max Angle:  ' + str(90) + 'Step Angle:  ' + str(self.step_angle)
            line07 = '### Measurement data ###'
            #line08 = 'OLEDVoltage	OLEDCurrent Photodiode Voltage'
            #line09 = 'V	              mA               V'
            #line10 = 'Angle    OLEDVoltage   	OLEDCurrent'
            #line11 = 'Degrees 	  V       	 A'
            line12 = 'Wavelength   Intensity'
            line13 = 'nm             -'
            
            #header_lines = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line08, line09] # PD Voltages
            #header_lines2 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line10, line11] # OLED Voltages
            header_lines3 = [line01, line02, linex, linexx, line03, line04, line05, line06, line07, line12, line13] # Spectrum Data
            
            "MOVING TO INITIAL POSITION"       
            DEVICES.PLmotor.move_to(self.min_angle) 
            time.sleep(self.homing_time)
            
            self.queue.put('\nOceanOptics : '+ str(DEVICES.MAYA_devices[0]))
            DEVICES.spec.integration_time_micros(self.integrationtime) 
                        
            "#####################################################################"
            "####TAKING MEASUREMENTS FROM THE OCEANOPTICS MAYALSL SPECTROMETER####"
            "#####################################################################"
            
            self.queue.put("\n\nSPECTROMETER READINGS") 
            
            "IMPLEMENTATION"
            # Generate empty lists for data collection
            ang = [] # Angles
            wvl = [] # Wavelengths
            inte = [] # Intensities
            spect = [] # Spectrums
            
            # Take calibration readings
            spectrum = DEVICES.spec.spectrum() # this gives a pre-stacked array of wavelengths and intensities
            np.savetxt(os.path.join(directory, mayafilename), spectrum.T, fmt='%.4f %.0f', delimiter='\t', header='\n'.join(header_lines3), comments='')
            processing_time = 0.5 # Initial processing time in seconds   
                        
            for angle in np.arange(self.min_angle, self.max_angle + 1, self.step_angle):           
                DEVICES.PLmotor.move_to(angle)
                time.sleep(self.moving_time)
                
                time.sleep(self.pulse_duration)                
                time.sleep(self.pulse_duration - processing_time)
                start_process = time.clock()
                
                wavelength = DEVICES.spec.wavelengths() # creates a list of wavelengths
                intensity = DEVICES.spec.intensities() # creates a list of intensities
                spectrum = DEVICES.spec.spectrum() # this gives a pre-stacked array of wavelengths and intensities
                wvl.append(wavelength) # adding to a master list (may not be necessary with txt file outputs)
                inte.append(intensity) # adding to a master list (may not be necessary with txt file outputs)
                spect.append(spectrum) # adding to a master list (may not be necessary with txt file outputs)
                                        
                "DISPLAYING SPECTRUM AS A PLOT"                            
                self.queue.put([wavelength,intensity])
                
                "SPECTRUM OUTPUT FILE"
                # Angle is written as 0 -> 180 rather than -90 -> 90
                if self.ang_range == 'F':
                    mayafilename = 'Angle'+str(angle + 90 - self.offset_angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                elif self.ang_range == 'HL':
                    mayafilename = 'Angle'+str(angle - self.offset_angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                elif self.ang_range == 'HR':
                    mayafilename = 'Angle'+str(self.offset_angle - angle).zfill(3)+'.txt' # changing mayalsl filename for actual readings
                mayafilename = os.path.abspath(os.path.join(mayafilepath, mayafilename))
                np.savetxt(mayafilename, spectrum.T, fmt='%.3f %.0f', delimiter='\t', header='\n'.join(header_lines3), comments='')
                end_process = time.clock()
                processing_time = end_process - start_process
                self.queue.put('\nProcessing time :  '+str(processing_time))
                
                if self.ang_range == 'F':
                    self.queue.put('\nAngle : '+str(angle + 90 - self.offset_angle))
                    ang.append(angle + 90 - self.offset_angle)
                elif self.ang_range == 'HL':
                    self.queue.put('\nAngle : '+str(angle - self.offset_angle))
                    ang.append(angle - self.offset_angle)
                elif self.ang_range == 'HR':
                    self.queue.put('\nAngle : '+str(self.offset_angle - angle))
                    ang.append(self.offset_angle - angle)
               
            self.queue.put('\n\nMEASUREMENT COMPLETE') 
                            
gui = GUI("GatherLab Goniometer Measurement System")
ELtab = gui.add_tab('EL Measurement',[1,2,3,4])
PLtab = gui.add_tab('PL Measurement',[1,2])
gui.run()