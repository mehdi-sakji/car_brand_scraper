FILE=./results/carnet.csv
if test -f "$FILE"; then
    cp $FILE ./results/carnet.bkp.csv
    rm -rf $FILE
fi
scrapy crawl carnet -o ./results/carnet.csv -t csv
