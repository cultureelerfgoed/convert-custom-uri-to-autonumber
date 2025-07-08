from rdflib import Graph, URIRef
from rdflib.namespace import SKOS
from rdflib.namespace import RDF

old_g = Graph()
new_g = Graph()
URI_dict = {}
id_iter = iter(range(1000000, 9999999))
base_URI = "https://vrouwenthesaurus.nl/id/"

# Parse RDF file
old_g.parse("Workspace/vrouwenthesaurus/pp_project_vrouwenthesaurus.ttl")

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

# Checks  
print(f"Dict URI_dict has {len(URI_dict)} entries")
print(f"Old graph has {len(old_g)} statements.")
print(f"New graph has {len(new_g)} statements.")
print(URI_dict.get("https://vrouwenthesaurus.nl/id/detectives", "No detectives"))
print(URI_dict.get("https://vrouwenthesaurus.nl/id/Sierra_Leone", "No Sierra Leone"))

# Print out the entire Graph in the RDF Turtle format
new_g.serialize(format="trig", destination="new_g.trig")