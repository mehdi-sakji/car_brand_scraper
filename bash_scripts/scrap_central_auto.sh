FILE=./results/central_auto.csv
if test -f "$FILE"; then
    cp $FILE ./results/central_auto.bkp.csv
    rm -rf $FILE
fi
scrapy crawl central_auto -o ./results/central_auto.csv -t csv
