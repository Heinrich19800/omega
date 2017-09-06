# omega
DayZ Standalone Server Administration Tool

Server plugin will come when server files have been released.

## Licensing

A client id and key can be acquired by contacting us

## APIs

To run the client Steam and IPHub API keys are required.

## todo

- [ ] mode that doesnt rely on cftools services and can work independently
- [ ] config files instead of requesting configs/serverlists from master
- [ ] scripts for starting/stopping (run client in background)
- [ ] remove unnecessary debugging blocks
- [ ] create server addon when the server files become available
- [ ] update observer to actually do something

### How to run client (foreground)

```
from time import sleep
import client

client = client.OmegaClient(
    client_id='CLIENT_ID', 
    client_key='CLIENT_KEY', 
    steam_api_key='STEAM_API_KEY',
    iphub_api_key='IPHUB_API_KEY'
)

while True:
    try:
        sleep(1)
        
    except Exception:
        break
```
