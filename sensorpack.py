#!/usr/bin/env python

##run the following command in the terminal and add the line after to the bottom of the file. The path should be wherever you have startup.sh saved. The path in startup.sh should also be edited if it's different to the default.
##sudo nano /etc/rc.local
##sudo /home/pi/Documents/startup.sh &


####### VALUES TO EDIT ##########

# runtime is the number of data points that will be generated minus the warmup. Take pollrate and warmup into account when deciding this. 'email' is the variable assigned to the user's email address.
## 200 runtime with pollrate of 3 results in ten minutes total (3 * 200 = 600 seconds), with 5 minutes of this being warmup that won't be written 

runtime = 200 
warmup = 100
receiver_email = "your@email.here"
pollrate = 3

#################################


##creates the errorlist, which stores what errors have come up, if any
errorlist = []


##attempts to import modules
try:
    import bme680
except (ModuleNotFoundError):
    errorlist.append("The BME680 module was not found! If the library has already been installed with 'curl https://get.pimoroni.com/bme680 | bash'  or 'sudo pip3 install bme680', then ensure that the path is not obstructed")
    pass
import time
import os
import email, smtplib, ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from gpiozero import Buzzer
try:
    from pms5003 import PMS5003
except (ModuleNotFoundError):
    errorlist.append("The BME680 module was not found! If the library has already been installed with 'sudo pip install pms5003', then ensure that the path is not obstructed")
    pass

##creates the buzzer for use later
buzzer = Buzzer(1)

# attempts to set up the BME680
try:
    try:
        sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
    except (RuntimeError, IOError):
        sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

    # These calibration data can safely be commented
    # out, if desired.

    print('Calibration data:')
    for name in dir(sensor.calibration_data):

        if not name.startswith('_'):
            value = getattr(sensor.calibration_data, name)

            if isinstance(value, int):
                print('{}: {}'.format(name, value))

    # These oversampling settings can be tweaked to
    # change the balance between accuracy and noise in
    # the data.

    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)
    sensor.set_filter(bme680.FILTER_SIZE_3)
    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

    print('\n\nInitial reading:')
    for name in dir(sensor.data):
        value = getattr(sensor.data, name)

        if not name.startswith('_'):
            print('{}: {}'.format(name, value))

    sensor.set_gas_heater_temperature(320)
    sensor.set_gas_heater_duration(150)
    sensor.select_gas_heater_profile(0)
    
    # Up to 10 heater profiles can be configured, each
    # with their own temperature and duration.
    # sensor.set_gas_heater_profile(200, 150, nb_profile=1)
    # sensor.select_gas_heater_profile(1)
    t = 0
except (NameError, ModuleNotFoundError, RuntimeError, IOError):
    errorlist.append("The BME680 was not detected! Check the wires are all properly connected or the i2c bus is enabled.")
    pass



## attempts to set up the PMS5003
try:
    pms5003 = PMS5003(
        device='/dev/ttyAMA0',
        baudrate=9600,
        pin_enable=27,
        pin_reset=22
    )
    data = pms5003.read()
except (NameError, ModuleNotFoundError, RuntimeError, IOError):
    errorlist.append("The PMS5003 was not detected! Check the wires are all properly connected, or if the serial port is not enabled type 'sudo raspi-config' and disable the login shell and enable serial port hardware under 'Interfacing options' and 'Serial'. You should then add 'enable_uart=1' and 'dtoverlay=pi3-miniuart-bt' to '/boot/config.txt'")
    pass


## if there has been at least one error, this will make the buzzer beep three times and write an error log. The if/else statement allows the sensor polling to be skipped in the event that there is an error.
if len(errorlist) > 0:
    buzznum=0
    while buzznum < 3:
        buzzer.off()
        time.sleep(1)
        buzzer.on()
        time.sleep(1)
        buzznum+=1
    errorstr="\n".join(errorlist)
    outfile= open("/media/pi/TOSHIBA/errorlog.txt","w")
    outfile.write(errorstr)
    filename = "/media/pi/TOSHIBA/errorlog.txt"
    outfile.close
## if there are no errors then this will run. The buzzer will beep once, then the output file will be written. The sensors will then begin to get polled, and after the warmup period has finished the values will be written to the output file.
else:
    try:
        buzzer.off()
        time.sleep(1)
        buzzer.on()
        n=1
        while os.path.isfile("/media/pi/TOSHIBA/testrun"+str(n)+".csv") is True:
            n=n+1
        outfile= open("/media/pi/TOSHIBA/testrun"+str(n)+".csv","w")
        outfile.write("Time,Temperature,Pressure,Humidity,pm >0.3um,pm >0.5um, pm >1.0um, pm >2.5um, pm >5um, pm >10um\n")
        filename = ("/media/pi/TOSHIBA/testrun"+str(n)+".csv")
        while True and t <= runtime:
    
        ## 2nd beep occurs when the warm up is finished
            if t == warmup:
                buzzer.off()
                time.sleep(1)
                buzzer.on()
            if sensor.get_sensor_data():
            ## sets data to the pms output
                data = pms5003.read()
            
                output = '{0:.2f},{1:.2f},{2:.2f},{3:.2f},{4:.2f},{5:.2f},{6:.2f},{7:.2f},{8:.2f}'.format(
                    sensor.data.temperature,
                    sensor.data.pressure,
                    sensor.data.humidity,
                    data.pm_per_1l_air(0.3),
                    data.pm_per_1l_air(0.5),
                    data.pm_per_1l_air(1.0),
                    data.pm_per_1l_air(2.5),
                    data.pm_per_1l_air(5),
                    data.pm_per_1l_air(10)
                    )
                print(output)
        ## if t>warmup, then the warm up is completed and the output file begins to get data written to it 
            if t > warmup:
            ## writes the timestamp
                outfile.write((time.strftime("%H:%M:%S"))+",")
            ## writes the output data
                outfile.write(output+"\n")
        
        ## final beep once the runtime is done
            if t == runtime:
                buzzer.off()
                time.sleep(1)
                buzzer.on()
                
            ## waits for the number of seconds determined in pollrate
            time.sleep(pollrate)
        
            t = t+1
    except KeyboardInterrupt:
        pass

    outfile.close()

## attempts to email either the errorlog or the output file depending on which occurred
try:
    subject = "Sensor results from sensor package"
    body = "These are the results from the last run of the sensor package."
    sender_email = "sensorpi858@gmail.com"
    password = "bioinfirp"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    with open(filename, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={filename}",
    )

    message.attach(part)
    text = message.as_string()

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)
except:
    pass

## turns off the sensor package if the runtime is greater than 30. This is to avoid the package becoming useless in the event that the runtime is so short that this file can't be edited. 
if runtime > 30:
    os.system('sudo shutdown now')
