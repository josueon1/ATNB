
import re

with open('app/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'taxa_mortalidade(?!_100k)', 'taxa_letalidade', content)
content = content.replace('Taxa de Mortalidade', 'Taxa de Letalidade')
content = content.replace('Mortalidade (%)', 'Letalidade (%)')

content = re.sub(r' +taxa_letalidade=\(\"taxa_letalidade\", \"mean\"\),\n +taxa_letalidade=\(\"taxa_letalidade\", \"mean\"\),\n', '            taxa_letalidade=(\"taxa_letalidade\", \"mean\"),\n', content)
content = re.sub(r'_agg_yr\[\"taxa_letalidade\"\] = _agg_yr\[\"taxa_letalidade\"\]\n', '', content)

with open('app/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Dashboard fixed!')

