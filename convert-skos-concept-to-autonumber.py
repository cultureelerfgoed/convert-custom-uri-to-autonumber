from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from rdflib.namespace import RDF
from pathlib import Path

# Configuration (Change these values according to your needs)

# Defines the range of the autonumber
autonumber_range = range(1000000, 9999999)

# Defines the input file path
# Currently only working for TTL..
input_file = "convert-skos-concept-to-autonumber/pp_project_vrouwenthesaurus.ttl"

# Defines the format of the output file
output_file_format = "trig"

# Defines the path of the output file
output_file = "convert-skos-concept-to-autonumber/vrouwenthesaurus-autonumber.trig"

# Base URI for the skos:Concepts
base_URI = "https://vrouwenthesaurus.nl/id/"

# Global variables 
graph = Graph(identifier=base_URI+"thesaurus")
URI_dict = {}
id_iter = iter(autonumber_range)

# Parse RDF file
print(f"Opening file: {str(Path.as_posix(Path.cwd())) +"/"+input_file}")
graph.parse(str(Path.as_posix(Path.cwd())) +"/"+input_file )
old_g_length = len(graph)

# Loop through each triple in the graph (subj, pred, obj)
for subj, pred, obj in graph:    
    # check whether subject contains base_URI, not already in key dictionary, and of RDF.type SKOS.concept
    if(base_URI in subj and str(subj) not in URI_dict.keys() and (URIRef(str(subj)), RDF.type, SKOS.Concept) in graph):
        # If so, add it to the key dictionary and increment ID iterator
        URI_dict.update({str(subj) : URIRef(base_URI + str(next(id_iter)))})        

    # check whether object contains base_URI, not already in key dictionary, and of RDF.type SKOS.concept
    if(base_URI in obj and str(obj) not in URI_dict.keys() and (URIRef(str(obj)), RDF.type, SKOS.Concept) in graph):        
        URI_dict.update({str(obj) : URIRef(base_URI + str(next(id_iter)))})        

    # Either add triple to graph as is, or as an updated triple.
    graph.remove((subj, pred, obj))
    graph.add((URI_dict.get(str(subj), subj), pred, URI_dict.get(str(obj), obj)))

# Test that the new graph contains as many triples as the old graph
assert(len(graph) == old_g_length)
print(f"Graph length (new vs. old): {len(graph)} == {old_g_length}.")

# Serialize new graph and write to output file
print(f"Writing output to: {Path.as_posix(Path.cwd())+"/"+output_file}")
graph.serialize(format=output_file_format, destination=str(Path.as_posix(Path.cwd())+"/"+output_file))

# Test that file wrote succesfully 
assert(Path(output_file).exists())