#!/usr/bin/env bash
set -e
mkdir -p docs tmp
cd tmp
git clone --depth 1 https://github.com/chandachewe10/loan-management-system lms
git clone --depth 1 https://github.com/MrShifu01/MicroFinance2 mf2
git clone --depth 1 https://github.com/tildemark/EquiYield eqy
cd ..
copy_readme() {
  f=$(ls "$1" | grep -i '^readme' | head -n1)
  cp "$1/$f" "docs/$2.txt"
}
copy_readme tmp/lms loan_mgmt_system
copy_readme tmp/mf2 microfinance_srs
copy_readme tmp/eqy equiyield
rm -rf tmp
wc -w docs/*.txt
