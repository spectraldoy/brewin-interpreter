from bparser import BParser
from argparse import ArgumentParser    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("source")

    args = parser.parse_args()

    with open(args.source, "r") as f:
        data = f.readlines()
    
    status, parsed_program = BParser.parse(data)

    print(parsed_program)

