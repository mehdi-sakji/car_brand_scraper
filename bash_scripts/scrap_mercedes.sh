FILE=./results/mercedes.csv
if test -f "$FILE"; then
    cp $FILE ./results/mercedes.bkp.csv
    rm -rf $FILE
fi
scrapy crawl mercedes -o ./results/mercedes.csv -t csv
