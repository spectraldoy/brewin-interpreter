from interpreterv3 import Interpreter
from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("source")

    args = parser.parse_args()

    with open(args.source, "r") as f:
        data = f.readlines()
    
    inter = Interpreter()
    inter.run(data)

