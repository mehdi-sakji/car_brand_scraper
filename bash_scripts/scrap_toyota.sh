FILE=./results/toyota.csv
if test -f "$FILE"; then
    cp $FILE ./results/toyota.bkp.csv
    rm -rf $FILE
fi
scrapy crawl toyota -o ./results/toyota.csv -t csv
