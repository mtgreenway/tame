import xml.etree.ElementTree as ET
import sys, os
import json, yaml, uuid, time, argparse
import requests

def load_config(config_filename):
    f = open(config_filename)
    config = yaml.safe_load(f)
    f.close()
    return config

def update_cghub_metadata(config, analysis, attachments):
    """
    Puts the given analysis
    If no "_id" in analysis, uses the one provided by couchdb
    """
    metadata_url = config["metadata_server"]["url"]
    cghub_db = config["metadata_server"]["tcga"]["cghub_database"]
    cghub_username = config["metadata_server"]["tcga"]["cghub_username"]
    cghub_password = config["metadata_server"]["tcga"]["cghub_password"]

    headers = {'content-type': 'application/json'}
    
    json_resp = None
    if "_id" in analysis:
        put_url = "".join([metadata_url, "/", cghub_db, "/", analysis["_id"]])
        put_response = requests.put(put_url, auth=(cghub_username, cghub_password), data=json.dumps(analysis), headers=headers, verify=False)
        if put_response.status_code != 201:
            print("ERROR: put response unexpected status code: %d" % put_response.status_code)
        else:
            json_resp = put_response.json()
    else:
        post_url = "".join([metadata_url, "/", cghub_db, "/"])
        post_response = requests.post(post_url, auth=(cghub_username, cghub_password), data=json.dumps(analysis), headers=headers, verify=False)
        if post_response.status_code != 201:
            print("ERROR: post response unexpected status code: %d %s" % (post_response.status_code, post_response.text))
        else:
            json_resp = post_response.json()

    return json_resp

def update_osdc_metadata(config, analysis, md5_ok=False, last_md5_check=None):
    """
    Takes in a TCGA analysis as a dictionary and adds the OSDC fields:
    downloaded, backedup, last_md5_check and md5_ok

    The analysis should contain a valid "_id" by now

    If a md5sum_file is specified

    If md5sum_ok is set to True md5_ok will be set to true and
    last_md5_check set to now.
    """
    #print("updating osdc metadata %s %s" % (md5_ok, last_md5_check))

    data_path = config["data_location"]["tcga"]["folder"]
    metadata_url = config["metadata_server"]["url"]
    osdc_db = config["metadata_server"]["tcga"]["osdc_database"]
    osdc_username = config["metadata_server"]["tcga"]["osdc_username"]
    osdc_password = config["metadata_server"]["tcga"]["osdc_password"]

    data_dir = "".join([data_path, "/", analysis["disease_abbr"], "/", analysis["analysis_id"]])
    osdc_url = "".join([metadata_url, "/", osdc_db, "/", analysis["_id"]])

    osdc_response = requests.get(osdc_url, verify=False)

    if osdc_response.status_code == 404:
        osdc_meta = {}
        osdc_meta["_id"] = analysis["_id"]
        osdc_meta["downloaded"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(data_dir)))
    elif osdc_response.status_code == 200:
        osdc_meta = osdc_response.json()

    #everthing is backedup...not doing anything with this field right now
    osdc_meta["backedup"] = True
    osdc_meta["md5_ok"] = md5_ok
    osdc_meta["last_md5_check"] = last_md5_check

    #print("osdc_meta: %s" % osdc_meta)
    osdc_resp = requests.put(osdc_url, auth=(osdc_username, osdc_password), data=json.dumps(osdc_meta), verify=False)
    if osdc_resp.status_code == 201:
        return osdc_resp.json()
    else:
        print("ERROR: osdc_resp has unexpected status code %d" % osdc_resp.status_code)


def load_cghub_metadata(config, xmlfile, md5filename=None):
    md5sums = {}
    md5time = None
    if md5filename is not None:
        md5time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(md5filename)))
        md5file = open(md5filename, "r")
        for line in md5file:
            sline = line.strip().split()
            if sline[1] == "True":
                md5sums[sline[0]] = True
            elif sline[1] == "False":
                md5sums[sline[1]] = False
            else:
                print("WARNING: unexpected md5sum value %s" % sline[1])
                
    #print("%s %s" % (md5time, md5sums))

    metadata_url = config["metadata_server"]["url"]
    cghub_db = config["metadata_server"]["tcga"]["cghub_database"]
    for event, result in ET.iterparse(xmlfile):
        elementdict = {}
        #in the cgquery generated xml files, don't have attachments - going to have to go out and get somehow?
        attachments = {}
        files = []
        errors = False

        if result.tag == "Result":
            for element in result:
                if element.tag == "files":
                    for file_element in element:
                        file_element_dict = {}
                        for file_property in file_element:
                            file_element_dict[file_property.tag] = file_property.text.strip()
                        files.append(file_element_dict)
                    elementdict[element.tag] = files
                elif element.tag == "analysis_xml" or element.tag == "experiment_xml" or element.tag == "run_xml":
                    if(len(element) < 1):
                        continue
                    else:
                        attachments[element.tag.replace("_", ".")] = ET.tostring(element[0])
                else:
                    if element.text is None:
                        elementdict[element.tag] = element.text
                    else:
                        elementdict[element.tag] = element.text.strip()

            if "disease_abbr" not in elementdict or elementdict["disease_abbr"] is None:
                print("No disease_abbr for " + elementdict["analysis_id"] + " skipping")
                result.clear()
                continue

            print("analysis_id\t" + elementdict["analysis_id"])

            analysis_url = "".join([metadata_url, "/", cghub_db, "/_design/find_docs/_view/by_analysis_id?key=", '"', elementdict["analysis_id"], '"'])
            #print("analysis_url\t" + analysis_url)
            exists_response = requests.get(analysis_url, verify=False).json()
            if "error" in exists_response:
                print(exists_response)

            num_rows = len(exists_response["rows"])

            if num_rows == 0:
                #analysis not in couchdb yet
                cghub_resp = update_cghub_metadata(config, elementdict, attachments)
                elementdict["_id"] = cghub_resp["id"]
                elementdict["_rev"] = cghub_resp["rev"]
                print("Added %s %s" % (cghub_resp["id"], cghub_resp["rev"]))
            elif num_rows == 1:
                #analysis already exists couchdb
                elementdict["_id"] = exists_response["rows"][0]["value"]["id"]
                elementdict["_rev"] = exists_response["rows"][0]["value"]["rev"]
                cghub_resp = update_cghub_metadata(config, elementdict, attachments)
                print("Updated %s %s" % (cghub_resp["id"], cghub_resp["rev"]))
            else:
                print("ERROR: found more than one metadata entry for %s skipping" % elementdict["analysis_id"])
                result.clear()
                continue

            if elementdict["analysis_id"] in md5sums:
                print("md5sum for %s" % elementdict["analysis_id"])
                osdc_resp = update_osdc_metadata(config, elementdict, md5sums[elementdict["analysis_id"]], md5time)
            else:
                print("no md5sum for %s" % elementdict["analysis_id"])
                osdc_resp = update_osdc_metadata(config, elementdict)

            result.clear()

def main():
    parser = argparse.ArgumentParser(description="Batch load CGHub metadata")
    parser.add_argument("-m", "--md5sum", metavar="filename", help="batch md5sum file", default=None)
    parser.add_argument("-c", "--config", metavar="filename", help="config file", default="config/local_config.yaml")
    parser.add_argument("xml", metavar="filename", help="XML containing CGHub metadata")
    args = parser.parse_args()
    config = load_config(args.config)
    load_cghub_metadata(config, args.xml, args.md5sum)

if __name__ == "__main__":
    main()
