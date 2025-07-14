"""Script allowing SKOS:Concepts in entity URI to be converted to an autonumber."""

from pathlib import Path
from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from rdflib.namespace import RDF

# Configuration (Change these values according to your needs)

# Defines the range of the autonumber
autonumber_range = range(1000000, 9999999)

# Defines the input file path
# Currently only working for TTL..
INPUT_FILE = "convert-skos-concept-to-autonumber/pp_project_vrouwenthesaurus.ttl"

# Defines the format of the output file
OUTPUT_FILE_FORMAT = "trig"

# Defines the path of the output file
OUTPUT_FILE = "convert-skos-concept-to-autonumber/vrouwenthesaurus-autonumber.trig"

# Base URI for the skos:Concepts
BASE_URI = "https://vrouwenthesaurus.nl/id/"

# Global variables 
graph = Graph(identifier=BASE_URI+"thesaurus")
uri_dict = {}
id_iter = iter(autonumber_range)

# Parse RDF file
print(f"Opening file: {str(Path.as_posix(Path.cwd())) +"/"+INPUT_FILE}")
graph.parse(str(Path.as_posix(Path.cwd())) +"/"+INPUT_FILE )
old_g_length = len(graph)

# Loop through each triple in the graph (subj, pred, obj)
for subj, pred, obj in graph:
    str_subj = str(subj)
    str_obj = str(obj)
    # check whether subject contains BASE_URI, not already in key dictionary, and of RDF.type SKOS.concept
    if(BASE_URI in subj and str_subj not in uri_dict.keys() and URIRef(str_subj), RDF.type, SKOS.Concept) in graph:
        # If so, add it to the key dictionary and increment ID iterator
        uri_dict.update({str(subj) : URIRef(BASE_URI + str(next(id_iter)))})

    # check whether object contains BASE_URI, not already in key dictionary, and of RDF.type SKOS.concept
    if(BASE_URI in obj and str_obj not in uri_dict.keys() and (URIRef(str_obj), RDF.type, SKOS.Concept) in graph):
        uri_dict.update({str_obj : URIRef(BASE_URI + str(next(id_iter)))})

    # Either add triple to graph as is, or as an updated triple.
    graph.remove((subj, pred, obj))
    graph.add((uri_dict.get(str_subj, subj), pred, uri_dict.get(str_obj, obj)))

# Test that the new graph contains as many triples as the old graph
assert len(graph) == old_g_length
print(f"Graph length (new vs. old): {len(graph)} == {old_g_length}.")

# Serialize new graph and write to output file
print(f"Writing output to: {Path.as_posix(Path.cwd())+"/"+OUTPUT_FILE}")
graph.serialize(format=OUTPUT_FILE_FORMAT, destination=str(Path.as_posix(Path.cwd())+"/"+OUTPUT_FILE))

# Test that file wrote succesfully
assert Path(OUTPUT_FILE).exists()
