# rtx2csv

CLI tool written in python to convert `.rtx` files into `.csv` files 

# Usage

clone the repo:
```
git clone https://github.com/TanmayPani/rtx2csv.git
cd rtx2csv
```


test the script:
```
python rtx_to_csv.py test/*.rtx test/outputs
```


Output should look like:
```
Converted 1 files in 0.8704216480255127 time!
```


check all arguments:
```
python rtx_to_csv.py -h 
```

(Optionally) set alias in `.bashrc`
```
alias rtx2csv="python rtx_to_csv.py"
```
