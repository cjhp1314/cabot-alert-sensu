from django.db import models
#from django.conf import settings
#from django.template import Context, Template

from cabot.cabotapp.alert import AlertPlugin, AlertPluginUserData

from os import environ as env

#import requests

sensu_port = env.get('SENSU_PORT') or '3030'
DEBUG = env.get('SENSU_DEBUG') or true          # TODO - set default to false

class SensuAlert(AlertPlugin):
    name = "Sensu"
    author = "Nicolas Truyens"

    def send_alert(self, service, users, duty_officers):
        debug = open("/var/log/cabot/alert_sensu.log", "a")
        if DEBUG:
            debug.write( 'Sending alert to Sensu.' )
        
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
            status = 0
        elif service.overall_status == service.WARNING_STATUS:
            status = 1
        elif service.overall_status == service.CRITICAL_STATUS:
            status = 2
        elif service.overall_status == service.ERROR_STATUS:
            status = 3
                
        outputs = list()
        for check in service.all_failing_checks():
            outputs.append(check.last_result().raw_data)
        
        output = ", ".join(outputs)
        
        if DEBUG:
            debug.write( 'source: ' + source + ' - name: ' + checkname + ' - status: ' + str(status) + ' - output: ' + output )        
        
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
            debug.write( 'handlers: ' + handlers )        
            
        self._send_sensu_alert(source=source, check=checkname, status=status, output=output, handlers=handlers)
        
        debug.close()
        
        return
    
    def _send_sensu_alert(self, source, check, status, output, handlers):
        URL = '/dev/tcp/localhost/' + sensu_port
        
        fo = open(URL, "w")        
        fo.write( '{"name": "'+check+'", "source": "'+source+'", "status": '+str(status)+', "output": "'+output+'", "handlers": '+handlers+' }' )            
        fo.close()
        
        if DEBUG:
            debug = open("/var/log/cabot/alert_sensu.log", "a")
            debug.write( 'SENDING {"name": "'+check+'", "source": "'+source+'", "status": '+str(status)+', "output": "'+output+'", "handlers": '+handlers+' } TO ' + URL )   
            debug.close()

class SensuAlertUserData(AlertPluginUserData):
     name = "Sensu Plugin"
     
     handlers = models.CharField(max_length=250, blank=True)
