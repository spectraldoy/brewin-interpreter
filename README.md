# Brewin# and Brewin++ Interpreters

This repository contains my implementations of the Brewin# and Brewin++ interpreters for UCLA's Spring 23 Programming Languages class. Brewin++ is a statically-typed, interpreted, object-oriented language, to which Brewin# extends exceptions and templated classes.

Sample Brewin++ programs can be found in the `v2` directory, and sample Brewin# programs can be found in the `v3` directory. These are structured the way they are so as to work with the `tester.py` and `harness.py` files, which implement an autograder. This autograder was provided to us and was not written by me. It comes from this repo: https://github.com/UCLA-CS-131/spring-23-autograder. The `intbase.py` (base interpreter) and `bparser.py` (Brewin parser) files were also provided to us, and come from here: https://github.com/UCLA-CS-131/spring-23-project-starter.

This project requires Python 3.11 to work correctly.

## Running a Brewin# program

Write a program in Brewin#. Then simply,

```sh
python3 main.py path/to/my/brewin#/file.brewin
```

## Running the test cases

```sh
python3 tester.py 2 # runs Brewin++ tests
python3 tester.py 3 # runs Brewin# tests
```

