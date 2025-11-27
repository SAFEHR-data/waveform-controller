A controller for reading waveform data from a rabbitmq queue and processing it. 

# Running the Code
## 1 Install and deploy EMAP
Follow the emap development [instructions](https://github.com/SAFEHR-data/emap/blob/main/docs/dev/core.md#deploying-a-live-version "Instructions for deploying a live version of EMAP") configure and deploy a version of EMAP. To run a local version you'll need to set 

```
  fake_uds:
    enable_fake_uds: true 
  uds:
    UDS_JDBC_URL: jdbc:postgresql://fakeuds:5432/fakeuds 
```

and configure and synthetic waveform generator

```
waveform:                                                     
  enable_waveform: true                                       
  enable_waveform_generator: true                             
  CORE_WAVEFORM_RETENTION_HOURS: 24                           
  WAVEFORM_HL7_SOURCE_ADDRESS_ALLOW_LIST: ALL
  WAVEFORM_HL7_TEST_DUMP_FILE: ""                             
  WAVEFORM_HL7_SAVE_DIRECTORY: "/waveform-saved-messages"
  WAVEFORM_SYNTHETIC_NUM_PATIENTS: 2                          
  WAVEFORM_SYNTHETIC_WARP_FACTOR:1                           
  WAVEFORM_SYNTHETIC_START_DATETIME: "2024-01-02T12:00:00Z"   
  WAVEFORM_SYNTHETIC_END_DATETIME: "2024-01-03T12:00:00Z"    
```

Once configured you can start it with 

```
emap docker up -d
```

## 2 Install and deploy waveform reader using uv

```
uv venv .waveform-controller
source .waveform-controller/bin/activate
uv pip install . --active
```

## 3 Check if it's working

If successful you should be able to run the demo script and see waveform messaged dumped to the terminal.
```
python waveform_controller.py
```

# Developing
See [developing docs](docs/develop.md)
