#!/bin/bash

export FLASK_APP=application.py
export FLASK_DEBUG=1
export DATABASE_URL=postgres://jfwvryvxzsnvjh:4720a7428a2edf7949646d85a879e24459ab1cce3a9d28396855ac2b89ddcab8@ec2-50-16-225-96.compute-1.amazonaws.com:5432/d8he45jl6l3h0e
export GOODREADS_KEY=hi6NmU2TkearHMdgVxhnZg

flask run
