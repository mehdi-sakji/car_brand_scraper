FILE=../results/toyota.csv
if test -f "$FILE"; then
    mv $FILE ../results/toyota.bkp.csv
fi
scrapy crawl toyota -o ../results/toyota.csv -t csv
