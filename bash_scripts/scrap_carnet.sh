FILE=../results/carnet.csv
if test -f "$FILE"; then
    mv $FILE ../results/carnet.bkp.csv
fi
scrapy crawl carnet -o ../results/carnet.csv -t csv
