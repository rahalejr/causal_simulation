import os
here = os.path.dirname(__file__)  # directory where this script is
json_path = os.path.join(here, "hit.json")

if __name__ == '__main__':
    with open(json_path) as f:
        data = f.read()

    with open(os.path.join(here, "collisions.js"), "w") as f:
        f.write("var data = " + data + ";")
