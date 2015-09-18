from django.db import models
#from django.conf import settings
#from django.template import Context, Template

from cabot.cabotapp.alert import AlertPlugin, AlertPluginUserData

from os import environ as env

import socket
import sys
import json
#import requests

sensu_port = env.get('SENSU_PORT') or 3030              # Integer required !!!
sensu_host = env.get('SENSU_HOST') or 'localhost'
DEBUG = env.get('SENSU_DEBUG') or True                  # TODO - set default to False

class SensuAlert(AlertPlugin):
    name = "Sensu"
    author = "Nicolas Truyens"

    def send_alert(self, service, users, duty_officers):
        if DEBUG:
            debug = open("/var/log/cabot/alert_sensu.log", "a")
            debug.write( 'Sending alert to Sensu.\n' )
        
        parts = service.name.split("_")
        if (len(parts) == 1 or len(parts) == 2):
             if (len(parts) == 1):
                source = 'network'
                checkname = service.name
             else:
                source = parts[0]
                checkname = parts[1]
        else:
            print "The service name should contain (maximum) 1 underscore to split up source and check name."
            # TODO - RAISE ERROR ?
            return
            
        if service.overall_status == service.PASSING_STATUS:
            status = '0'
        elif service.overall_status == service.WARNING_STATUS:
            status = '1'
        elif service.overall_status == service.CRITICAL_STATUS:
            status = '2'
        elif service.overall_status == service.ERROR_STATUS:
            status = '3'
                
        extra_info = dict()
        for check in service.all_failing_checks():
            result = check.last_result()
            
            raw_data = json.loads(result.raw_data)
            
            extra_info[check.name] = { 'metric': check.metric, 'took': result.took+' ms', 'error': result.error, 'raw_data': result.raw_data }
            
        output = 'Service '+service.name+': '+str(service.overall_status)
        exta_data = ', "extra_info": "'+json.dumps(extra_info)+'"'
        
        if DEBUG:
            debug.write( 'source: ' + source + ' - name: ' + checkname + ' - status: ' + status + ' - output: ' + output + ' - extra_data: ' + exta_data + '\n' )        
        
        handlerList = list()         
        for user in users:
            try:
                userData = SensuAlertUserData.objects.get(user=user, title=SensuAlertUserData.name)
                userHandlers = userData.handlers
                parts = userHandlers.split(",")
                for part in parts:
                    handlerList.append('"'+part+'"')
            except:
                pass
            
        uniqueHandlerList = set(handlerList)
        handlers = "[" + ",".join(uniqueHandlerList) + "]"
                
        if DEBUG:
            debug.write( 'handlers: ' + handlers + '\n' )        
            debug.close()
            
        self._send_sensu_alert(source=source, check=checkname, status=status, output=output, handlers=handlers, exta_data=exta_data)
                
        return
    
    def _send_sensu_alert(self, source, check, status, output, handlers, exta_data=''):
        try: 
            port = int(sensu_port)
        except ValueError:
            port = sensu_port
                
        ADDR = (sensu_host, port)
        DATA = '{"name": "'+check+'", "source": "'+source+'", "status": '+status+', "output": "'+output+'", "handlers": '+handlers+exta_data+' }'
        
        if DEBUG:
            debug = open("/var/log/cabot/alert_sensu.log", "a")
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                         
            if DEBUG:
                debug.write('Connecting to '+sensu_host+' on port '+str(port)+'\n')
                
            s.connect(ADDR)
            if DEBUG:
                debug.write('Connected!\n')
                    
            s.send(DATA)
            if DEBUG:
                debug.write('Sent Data: '+DATA+'\n')
                            
            s.close()
        except socket.error, msg:
            print('Exception: ' + msg + '\n')
            if DEBUG:
                debug.write('Exception: ' + msg + '\n')                
        
        if DEBUG:
            debug.close() 

class SensuAlertUserData(AlertPluginUserData):
     name = "Sensu Plugin"
     
     handlers = models.CharField(max_length=250, blank=True)
