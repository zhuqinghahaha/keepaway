#!/bin/bash
echo "building keepaway player"
cd /home/soccer/keepaway/player
make
echo "going to sleep"
sleep 40  # let theano process neural network
echo "starting keepaway in sync mode"
cd /home/soccer
./keepaway/keepaway.py --field-length=${FIELD_SIZE:-20} --field-width=${FIELD_SIZE:-20} --keeper-policy=dql --keeper-learn --keeper-output=logs/keeper.out --log-dir=logs/ --synch-mode

