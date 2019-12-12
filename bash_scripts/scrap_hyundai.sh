FILE=./results/hyundai.csv
if test -f "$FILE"; then
    cp $FILE ./results/hyundai.bkp.csv
    rm -rf $FILE
fi
scrapy crawl hyundai -o ./results/hyundai.csv -t csv
