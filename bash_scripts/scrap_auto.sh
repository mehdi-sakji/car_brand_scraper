FILE=./results/auto.csv
if test -f "$FILE"; then
    cp $FILE ./results/auto.bkp.csv
    rm -rf $FILE
fi
scrapy crawl auto -o ./results/auto.csv -t csv
