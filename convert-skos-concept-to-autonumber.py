from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from rdflib.namespace import RDF
from pathlib import Path

# Configuration (Change these values according to your needs)

# Defines the range of the autonumber
autonumber_range = range(1000000, 9999999)

# Defines the input file path
input_file = "convert-skos-concept-to-autonumber/pp_project_vrouwenthesaurus.ttl"

# Defines the format of the output file
output_file_format = "trig"

# Defines the path of the output file
output_file = "convert-skos-concept-to-autonumber/vrouwenthesaurus-autonumber.trig"

# Base URI for the skos:Concepts
base_URI = "https://vrouwenthesaurus.nl/id/"

# Global variables 
old_g = Graph()
new_g = Graph()
URI_dict = {}
id_iter = iter(autonumber_range)

# Parse RDF file
print(f"Opening file: {str(Path.as_posix(Path.cwd())) +"/"+input_file}")
old_g.parse(str(Path.as_posix(Path.cwd())) +"/"+input_file )

# Copy namespace to new graph
for ns_prefix, ns in old_g.namespaces():    
    new_g.bind(ns_prefix, ns)

# Loop through each triple in the graph (subj, pred, obj)
for subj, pred, obj in old_g:    
    # check whether subject contains base_URI, not already in key dictionary, and of RDF.type SKOS.concept
    if(base_URI in subj and str(subj) not in URI_dict.keys() and (URIRef(str(subj)), RDF.type, SKOS.Concept) in old_g):
        # If so, add it to the key dictionary and increment ID iterator
        URI_dict.update({str(subj) : URIRef(base_URI + str(next(id_iter)))})        
        new_g.add((URI_dict[str(subj)], pred, obj))

    else:
        # Otherwise it is either not a new key, or a reference, or just another triple, so add accordingly.
        new_g.add((URI_dict.get(str(subj), subj), pred, URI_dict.get(str(obj), obj)))

# Second pass in case concept was mentioned as broader before concept definition
for subj, pred, obj in new_g:    
    if(str(subj) in URI_dict.keys() or str(obj) in URI_dict.keys()):
        new_g.remove((subj, pred, obj))
        new_g.add((URI_dict.get(str(subj), subj), pred, URI_dict.get(str(obj), obj)))

# Tests
assert(len(old_g) == len(new_g))

# Serialize new graph and write to output file
print(f"Writing output to: {Path.as_posix(Path.cwd())+"/"+output_file}")
new_g.serialize(format=output_file_format, destination=str(Path.as_posix(Path.cwd())+"/"+output_file))