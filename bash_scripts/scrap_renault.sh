FILE=../results/renault.csv
if test -f "$FILE"; then
    mv $FILE ../results/renault.bkp.csv
fi
scrapy crawl renault -o ../results/renault.csv -t csv
