FILE=../results/subaru.csv
if test -f "$FILE"; then
    mv $FILE ../results/subaru.bkp.csv
fi
scrapy crawl subaru -o ../results/subaru.csv -t csv
