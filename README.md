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

## 2 Install and deploy waveform controller using docker

Create a root directory for your installation of the waveform-controller project,
separate to the Emap project root.

### Expected top-level dir structure
```
├── PIXL
├── config
├── waveform-controller
└── waveform-export
```

### Instructions for achieving this structure

Clone this repo (`waveform-controller`) and [PIXL](https://github.com/SAFEHR-data/PIXL),
both inside your root directory.

Set up the config files as follows:
```
mkdir config
cp waveform-controller/config.EXAMPLE/controller.env.EXAMPLE config/controller.env
cp waveform-controller/config.EXAMPLE/exporter.env.EXAMPLE config/exporter.env
cp waveform-controller/config.EXAMPLE/hasher.env.EXAMPLE config/hasher.env
```
From the new config files, remove the comments telling you not to put secrets in it, as instructed.

If it doesn't already exist you should create a directory named
`waveform-export` in the parent directory to store the saved waveform
messages.

```
mkdir waveform-export
```

Build and start the controller and exporter with docker
```
cd waveform-controller
docker compose build
docker compose up -d
```

## 3 Check if it's working

Running the controller will save (to `../waveform-export`) waveform messages
matched to Contact Serial Number (CSN) as csv files, each containing data for
one calender day, as
`YYYY-MM-DD.CSN.sourceName.units.csv`

Each row of the csv will contain

`csn, mrn, units, samplingRate, observationTime, waveformData`

## Perform a parquet conversion (including de-id)
At the time of writing, the cron pipeline is not set up. This section shows
how to perform an ad-hoc de-id.
```
docker compose run waveform-controller emap-csv-pseudon  --csv /waveform-export/original-csv/my_original_csv.csv
```

## Perform an export
At the time of writing, the cron pipeline is not set up. This section shows
how to perform an ad-hoc FTPS upload.

Exported files must be under the WAVEFORM_PSEUDONYMISED_PARQUET directory.
Files passed in must be given relative to this directory:
```
docker compose run --entrypoint "" waveform-exporter emap-send-ftps my_pseudonymised_file.parquet
```

# Developing
See [developing docs](docs/develop.md)
