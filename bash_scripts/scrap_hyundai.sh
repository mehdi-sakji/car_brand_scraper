FILE=../results/hyundai.csv
if test -f "$FILE"; then
    mv $FILE ../results/hyundai.bkp.csv
fi
scrapy crawl hyundai -o ../results/hyundai.csv -t csv
