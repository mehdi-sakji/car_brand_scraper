FILE=./results/subaru.csv
if test -f "$FILE"; then
    cp $FILE ./results/subaru.bkp.csv
    rm -rf $FILE
fi
scrapy crawl subaru -o ./results/subaru.csv -t csv
