#encoding: utf-8

# for generateing encryption table
seed  = 8127389

#-- client --#
# bind ip
forward_host = '0.0.0.0'

# bind port
forward_port = 9999

# connect server ip (only for client; the server would bind on 0.0.0.0)
server_host = '127.0.0.1'


#-- server --#
# bind ip
server_port = 9998

try:
    debug = False
    from local_config import *
except:
    pass
