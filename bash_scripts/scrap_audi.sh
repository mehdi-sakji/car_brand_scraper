FILE=./results/audi.csv
if test -f "$FILE"; then
    cp $FILE ./results/audi.bkp.csv
    rm -rf $FILE
fi
scrapy crawl audi -o ./results/audi.csv -t csv
