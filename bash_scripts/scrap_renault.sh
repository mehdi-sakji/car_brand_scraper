FILE=./results/renault.csv
if test -f "$FILE"; then
    cp $FILE ./results/renault.bkp.csv
    rm -rf $FILE
fi
scrapy crawl renault -o ./results/renault.csv -t csv
