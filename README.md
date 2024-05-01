# app-openlca-export
Exports Materials and Processes as OpenLCA Processes and Flows

This app can run standalone or deployed via https://github.com/OpenSemanticWorld/python-docker-app

## Configuration

Reference data must be provided by exporting flow properties and units from OpenLCA (as zipped JSON-LD files, see `OPENLCA_REFDATA_PATH`)

### Environment Variables

| Name        | Example           | Description  |
| ------------- |:-------------| :-----|
| OSW_SERVER      | https://demo.open-semantic-lab.org | Root url of the target instance |
| OPENLCA_EXPORT_CATEGORY      | OSL Export | Name of the OpenLCA Category for exported flows and processes |
| OPENLCA_REFDATA_PATH      | openlca_2_elcd_background_data.zip | Filepath for the background data, relative to pn_app.py |

Example .env file
```env
OSW_SERVER = 'https://demo.open-semantic-lab.org'
OPENLCA_EXPORT_CATEGORY = "OSL Export"
OPENLCA_REFDATA_PATH = 'openlca_2_elcd_background_data.zip'
```

## Screenshot
![tempsnip](https://github.com/OpenSemanticLab/app-openlca-export/assets/52674635/c84f4a34-6b8b-41f4-9690-478b6b8f4614)
