"""
A simple example showing iterating over the tree.
"""
from keepassdb import Database


def print_group(group, level=0):
    print (" " * level) + group.title
    for entry in group.entries:
        print (" " * level) + " -" + entry.title
    for child in group.children:
        print_group(child, level+1)

if __name__ == '__main__':
    db = Database('./example.kdb', password='test')    
    print_group(db.root)

