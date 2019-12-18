FILE=../results/central_auto.csv
if test -f "$FILE"; then
    mv $FILE ../results/central_auto.bkp.csv
fi
scrapy crawl central_auto -o ../results/central_auto.csv -t csv
