from xml.etree import ElementTree
import sys, os
import json, yaml, uuid, time, argparse
import requests

def load_config(config_filename):
    f = open(config_filename)
    config = yaml.safe_load(f)
    f.close()
    return config

def get_cghub_metadata(disease_abbr, config):
    """
    Fetches the CGHub metadata for a given disease. Returns ElementTree of the XML.
    Only going to allow filtering the metadata by disease 
    Not getting raw analysis XML at this stage, so going to load everything into memory
    """
    cghub_url = config["cghub_metadata_server"]["url"]
    cghub_query_url = cghub_url + "?disease_abbr=" + disease_abbr
    cghub_response = requests.get(cghub_query_url)
    
    if cghub_response.status_code != 200:
        print("ERROR: get response from CGHub metadata server unexpected status code: %d, exiting." % cghub_response.status_code)
        sys.exit(-1)

    cghub_tree = ElementTree.fromstring(cghub_response.content)
    return cghub_tree

def get_local_metadata(disease_abbr, config):
    # do we want to index this by analysis id? I think we do...
    return {}

def cghub_to_json(cghub_metadata):
    results = []
    for result in cghub_metadata.findall("Result"):
        result_json = {}
        
        for elem in result:
        #can't figure out good general solution, so making exception for file
            if elem.tag.lower() == "files":
                files = []
                for file_elem in elem:
                    file_dict = {}
                    for file_property in file_elem:
                        file_dict[file_property.tag] = file_property.text.strip()
                        files.append(file_dict)
                        result_json[elem.tag.lower()] = files
                        
            else:       
                if elem.text is None:
                    result_json[elem.tag.lower()] = elem.text
                else:
                    result_json[elem.tag.lower()] = elem.text.strip()
    
        results.append(result_json)

    return results

def compare_metadata(cghub_metadata, local_metadata, config):
    """
    Returns a list of new and updated analyses by comparing the CGHub XML to our local couchdb
    """
    cghub_json = cghub_to_json(cghub_metadata)
    #ones that require running gene torrent
    analyses_to_download = []
    #ones that only require updating something about the metadata - does this happen?
    analyses_to_update = []

    for result in cghub_json:
        if result["analysis_id"] in local_metadata:
            #then need to compare
            print("in local metadata")
        else:
            #then this is a new one
            new_analyses.append(result)

    print new_analyses
    
def main():
    parser = argparse.ArgumentParser(description="Update TCGA metadata from CGHub")
    parser.add_argument("-c", "--config", metavar="filename", help="config file", default="config/local_config.yaml")
    parser.add_argument("disease_abbr", help="CGHub Disease to Update")
    args = parser.parse_args()
    config = load_config(args.config)
    cghub_metadata = get_cghub_metadata(args.disease_abbr, config)
    local_metadata = get_local_metadata(args.disease_abbr, config)
    compare_metadata(cghub_metadata, local_metadata, config)

if __name__ == "__main__":
    main()
