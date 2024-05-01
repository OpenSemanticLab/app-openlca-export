
from pprint import pprint
import olca_schema as o
import olca_schema.zipio as zipio

import os


import osw.model.entity as model
from osw.auth import CredentialManager
from osw.core import OSW
from osw.wtsite import WtSite
from osw.utils.wiki import get_full_title

#Panels
from io import StringIO
import os
from typing import List
import panel as pn
import pandas as pd
import datetime as dt

from bokeh.models.widgets.tables import NumberFormatter, BooleanFormatter, HTMLTemplateFormatter

from osw.core import OSW
from osw.auth import CredentialManager
import osw.wiki_tools as wt
import osw.model.entity as model
from osw.utils.wiki import get_full_title
from osw.wtsite import WtSite

class OpenLcaValueError(ValueError):
    pass

current_dir = os.path.dirname(os.path.abspath(__file__))
refdata = os.environ.get('OPENLCA_REFDATA_PATH')

def init_osw():
    # create/update the password file under examples/accounts.pwd.yaml
    pwd_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "accounts.pwd.yaml"
    )
    wtsite = WtSite(
        config=WtSite.WtSiteConfig(
            iri=os.environ.get('OSW_SERVER'),
            cred_mngr=CredentialManager(cred_filepath=pwd_file_path),
        )
    )

    osw = OSW(site=wtsite)
    return osw

def init(osw):
    # Load Schemas on demand
    if not hasattr(model, "EnergyForm"):
        osw.fetch_schema(
            OSW.FetchSchemaParam(
                schema_title=[
                    "Category:OSWbdc4fb3bd13940268cd58a4fd6d13c95", # ProcessFlow
                    "Category:OSW10b8d9a3251d42f5b1bd431687a8c408", # MaterialCompound
                    "Category:OSW0583b134c618484c9911a3dff145c7eb", # ChemicalCompound
                    "Category:OSW1b15ddcf042c4599bd9d431cbfdf3430", # MainQuantityProperty
                    "Category:OSWabd18c58548c4f0894015a54d80ce21a", # MaterialCategory
                    "Category:OSW4e964dd422a747bc955b1ffe8886c277", # CostCategory
                    "Category:OSW6028b7ca1f6342cb929584d64cc88d3c", # EnergyForm
                ], mode="replace"
            )
        )


def test():
    # create a unit group and flow property
    units = o.new_unit_group('Units of mass', 'kg')
    kg = units.units[0]
    mass = o.new_flow_property('Mass', units)
    mass.uuid

    # create a product flow and a process with the product as output
    steel = o.new_product('Steel', mass)
    process = o.new_process('Steel production')
    output = o.new_output(process, steel, 1, kg)
    output.is_quantitative_reference = True

    # prints the Json string of the process
    print(process.to_json())

    # write a zip package with the data sets
    with zipio.ZipWriter('openlca_example.zip') as w:
        for entity in [units, mass, steel, process]:
            w.write(entity)

olca_units = {}
# defailt mapping: directly use the symbol as unit name
osw_olca_unit_mapping = {
    "€": "EUR"
}
olca_flow_properties = {}
# defailt mapping: strip "Property:Has" from the quantity name
osw_olca_flow_property_mapping = {
    "MonetaryValue": "Cost"
}
def build_index():

    with zipio.ZipReader(os.path.join(current_dir, refdata)) as r:
        for ug_uuid in r.ids_of(o.UnitGroup):
            ug = r.read(o.UnitGroup, ug_uuid)
            #print(ug.name)
            for u in ug.units:
                #print(u.name)
                olca_units[u.name] = u
        for fp_uuid in r.ids_of(o.FlowProperty):
            fp = r.read(o.FlowProperty, fp_uuid)
            #print(fp.name)
            olca_flow_properties[fp.name] = fp
    #print(olca_units["kg"])
    #print(olca_flow_properties["Mass"])

def export(osw, process_flows = None):
    osw.site.enable_cache()

    if process_flows is None:
        process_flows = osw.query_instances(category="Category:OSWbdc4fb3bd13940268cd58a4fd6d13c95")
        #process_flows = ["Item:OSW47bc0774d2e34a01910465d6bc3c047e"]
        #process_flows = ["Item:OSW8a71c2eef9dd4ff5872df365bc897c18"]
    export_category = os.environ.get('OPENLCA_EXPORT_CATEGORY') # subcategories can be added with a slash, e.g. "MyCategory/Solvent"
    olca_export_processes = {}
    olca_export_flows = {}

    for pf in process_flows:
        wp = osw.load_entity(pf).cast(model.ProcessFlow)
        url = osw.site._site.scheme + "://" + osw.site._site.host + osw.site._site.path + "index.php?title=" + get_full_title(wp)
        print(f"Exporting {wp.label[0].text} ({wp.uuid}) from {url}")
        op = o.Process(
            id=str(wp.uuid),
            name=wp.label[0].text,
            description=wp.description[0].text if wp.description else "",
            category=export_category,
            process_type=o.ProcessType.UNIT_PROCESS,
            exchanges=[],
        )
        exchanges = []
        for wf in wp.input_materials if wp.input_materials else []:
            exchanges.append({"is_input": True, "flow": wf})
        for wf in wp.input_energy if wp.input_energy else []:
            exchanges.append({"is_input": True, "flow": wf})
        for wf in wp.costs if wp.costs else []:
            exchanges.append({"is_input": True, "flow": wf})
        for wf in wp.output_materials if wp.output_materials else []:
            exchanges.append({"is_input": False, "flow": wf})
        for wf in wp.output_energy if wp.output_energy else []:
            exchanges.append({"is_input": False, "flow": wf})


        for wex in exchanges:

            try:
                wf = wex["flow"]
                is_input = wex["is_input"]
                m = osw.load_entity(wf.object).cast(model.Material)
                mc = []
                for c in m.material_categories if m.material_categories else []:
                    c = osw.load_entity(c).cast(model.MaterialCategory)
                    mc.append(c.label[0].text)

                of = o.Flow(
                    id=str(m.uuid),
                    name=m.label[0].text,
                    description=m.description[0].text if m.description else "",
                    category=export_category,
                    tags=mc,
                    flow_type=o.FlowType.PRODUCT_FLOW,
                    
                )
                olca_export_flows[of.id] = of
                
                try:

                    qst = None # the quantity statement
                    q = None # the quantity of the quantity statement
                    q_name = None # the name of the quantity
                    u = None # the unit of the quantity statement
                    u_sym = None # the symbol of the unit of the quantity statement
                    for st in wf.substatements:
                        if st.quantity is not None:
                            qst = st
                            u_uuid = osw.get_uuid(qst.unit.split("#")[1])
                            q = osw.load_entity(st.quantity).cast(model.MainQuantityProperty)
                            q_name = q.name.replace("Property:", "").replace("Has", "")
                            if q_name in osw_olca_flow_property_mapping:
                                q_name = osw_olca_flow_property_mapping[q_name]
                            all_units = [q.main_unit]
                            if q.additional_units: all_units += q.additional_units
                            for unit in all_units:
                                if unit.uuid == u_uuid:
                                    u = unit
                                    if unit.main_symbol in osw_olca_unit_mapping:
                                        u_sym = osw_olca_unit_mapping[unit.main_symbol]
                                    else: u_sym = unit.main_symbol
                                    break
                            break # we take the first

                    if qst is None:
                        raise OpenLcaValueError("No quantity statement found")
                    if q is None:
                        raise OpenLcaValueError("Quantity not found")
                    if u is None:
                        raise OpenLcaValueError("Unit definition not found")
                    if olca_units.get(u_sym) is None:
                        raise OpenLcaValueError(f"Unit {u_sym} not found in olca_units")
                    if olca_flow_properties.get(q_name) is None:
                        raise OpenLcaValueError(f"Flow property {q_name} not found in olca_flow_properties")

                    of.flow_properties=[o.FlowPropertyFactor(
                        conversion_factor=1.0,
                        is_ref_flow_property=True,
                        flow_property=olca_flow_properties.get(q_name)
                    )]
                    of.refUnit=u_sym
                    olca_export_flows[of.id] = of

                    oex = o.Exchange(
                        amount=float(qst.numerical_value),
                        flow=of,
                        flow_property=olca_flow_properties.get(q_name),
                        unit=olca_units.get(u_sym),
                        is_input=is_input,
                        is_quantitative_reference=True,
                    )

                except OpenLcaValueError as e:
                    print(f"Warning: ", e)
                    oex = o.Exchange(
                        flow=of,
                        is_input=is_input,
                        is_quantitative_reference=True,
                    )
                op.exchanges.append(oex)

            except Exception as e:
                print(f"Error: ", e)
        olca_export_processes[op.id] = op
        #pprint(op)

    return olca_export_flows, olca_export_processes

def create_zip_file(olca_export_flows, olca_export_processes):
    version = "2.0.0"
    key_mapping = {
        "avoidedProduct": "isAvoidedProduct",
        "input": "isInput",
        "quantitativeReference": "isQuantitativeReference",
    }


    # write a zip package with the data sets
    filepath = os.path.join(current_dir, 'openlca_export.zip')
    if os.path.exists(filepath):
        os.remove(filepath)
    with zipio.ZipWriter(filepath) as w:
        for key in olca_export_flows:
            d = olca_export_flows[key]
            w.write(d)
        for key in olca_export_processes:
            d = olca_export_processes[key]
            if version == "1.0.0":
                for ex in d.exchanges if d.exchanges else []:
                    for k, v in key_mapping.items():
                        if ex.get(v) is not None:
                            ex[k] = ex.pop(v)
            w.write(d)

def createApp():

    if not 'osw' in pn.state.cache:
        print("Invalid session")
        osw = init_osw()
        """cred_mngr=CredentialManager(

        )
        cred_mngr.add_credential(
            CredentialManager.UserPwdCredential(
                iri="wiki-dev.open-semantic-lab.org", username="<username>", password="<password>"
            )
        )
        cred = cred_mngr.get_credential(CredentialManager.CredentialConfig(iri="")) # this will select the first entry

        site = WtSite(
            WtSite.WtSiteConfig(
                iri=cred.iri,
                cred_mngr=cred_mngr
            )
        )
        osw = OSW(
            site=site
        )"""
    else:
        osw: OSW = pn.state.cache['osw']
        user = pn.state.cache['osw_user']
        print(user)
    
    init(osw)
    build_index()
    titles = wt.semantic_search(osw.site._site, wt.SearchParam(
        query="[[HasType::Category:OSWbdc4fb3bd13940268cd58a4fd6d13c95]]",
        limit=25,
    ))
    print(titles)

    results = []
    result_dict = {
        #"index": [],
        "id": [],
        "name": [],
        "link": [],
        #"include": [],
    }
    articles : List[model.Article] = osw.load_entity(titles)
    index = 0
    for article in articles:
        #result_dict["index"].append(index)
        result_dict["id"].append(str(article.uuid))
        result_dict["name"].append(article.label[0].text)
        #result_dict["link"].append({
        #    "url": os.getenv("OSW_SERVER") + "/wiki/",
        #    "value": article.label[0].text
        #})
        result_dict["link"].append(os.environ.get('OSW_SERVER') + "/wiki/" + get_full_title(article))
        #result_dict["include"].append(True)
        
        #results.append(article.json())
        results.append(result_dict)
        index += 1

    df = pd.DataFrame({
        'int': [1, 2, 3],
        'float': [3.14, 6.28, 9.42],
        'str': ['A', 'B', 'C'],
        'bool': [True, False, True],
        'date': [dt.date(2019, 1, 1), dt.date(2020, 1, 1), dt.date(2020, 1, 10)],
        'datetime': [dt.datetime(2019, 1, 1, 10), dt.datetime(2020, 1, 1, 12), dt.datetime(2020, 1, 10, 13)]
    })#, index=[1, 2, 3])
    df = pd.DataFrame(result_dict)

    bokeh_formatters = {
        'float': NumberFormatter(format='0.00000'),
        #'include': BooleanFormatter(),
        'link': HTMLTemplateFormatter(template='<a href="<%= value %>" target="_blank">link</a>')
    }
    """ {
            "_data": results,
            "_columns": [
                {"title":"ID", "field":"id"},
                {"title":"name", "field":"name"},
                {"title":"link", "field":"link"},
                {"title":"include", "field":"include"}
                ]
            } """
    result_tab = pn.widgets.Tabulator(df, formatters=bokeh_formatters, selectable='checkbox')#, buttons={'Print': "<i class='fa fa-print'></i>"})

    #def click(event):
    #    print(f'Clicked cell in {event.column!r} column, row {event.row!r} with value {event.value!r}')
    #result_tab.on_click(click)

    def filtered_file():
        export_titles = [url.split("/")[-1] for url in result_tab.selected_dataframe["link"]]
        print("Export: ", export_titles)
        (olca_export_flows, olca_export_processes) = export(osw, export_titles)
        create_zip_file(olca_export_flows, olca_export_processes)
        return open(os.path.join(current_dir, 'openlca_export.zip'), "rb")

    download_btn = pn.widgets.FileDownload(
        file=os.path.join(current_dir, refdata), button_type='success', auto=False,
        embed=False, name="Background data. Left-click, then Right-click to download using 'Save as' dialog"
    )
    fd = pn.widgets.FileDownload(
        callback=pn.bind(filtered_file), filename='openlca_export.zip'
    )

    def callback(e):
        print(result_tab.selection)
        #result_tab.selected_dataframe
    btn = pn.widgets.Button(name='Export', button_type='primary')
    btn.on_click(callback)

    row = pn.Row(result_tab, fd, download_btn)

    return row

if __name__ == "__main__":
    build_index()
    
    #(olca_export_flows, olca_export_processes) = export()
    #create_zip_file(olca_export_flows, olca_export_processes)

    #pn.serve(createApp(osw), port=5007)
    pn.serve(createApp(), port=5007)

