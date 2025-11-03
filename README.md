# rtx2csv

CLI tool written in pure python to convert `.rtx` files produced from Renishaw XL-80 dynamic captures into `.csv` files 

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


Output on the terminal should look like:
```
Converted 1 files in 0.8704216480255127 time!
```
look in `test/outputs` folder for a folder with the same basename as the `.rtx` file containing `header.json` and `data.csv` files

check all the arguments that can be set:
```
$ python rtx_to_csv.py -h
usage: rtx_to_csv.py [-h] [--reduceby REDUCEBY] [--reduction {mean,drop}] [--chunk_size CHUNK_SIZE] input output_dir

convert .rtx files into .csv files

positional arguments:
  input                 path to an .rtx file or a glob expression
  output_dir            path to folder to store the output files in

options:
  -h, --help            show this help message and exit
  --reduceby REDUCEBY   factor to reduce sampling rate by
  --reduction {mean,drop}
                        how to apply reduction to sampling rate
  --chunk_size CHUNK_SIZE
                        amount of data (in bytes) to read at once from a .rtx file
```

(Optionally) set alias in `.bashrc`
```
alias rtx2csv="python /path/to/rtx2csv/rtx_to_csv.py"
```

has been tested in `Python 3.13.9` on Fedora 42
