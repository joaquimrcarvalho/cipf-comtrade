# Principais produtos nas trocas entre a China e os PLP

A análise dos principais produtos nas trocas entre a China e os Países de Língua Portuguesa (PLP).

O objetivo é identificar os produtos mais importantes nas trocas comerciais entre a China e os PLP, bem como a evolução da
composição das trocas ao longo do tempo.

Os dados são gerados pelo  bloco de notas [cn_plp_commodities.ipynb](cn_plp_commodities.ipynb) que utiliza a base de dados Comtrade da ONU.

As categorias de produtos são baseadas no "Harmonized System" (HS) de classificação de mercadorias. O HS é um sistema de classificação de mercadorias utilizado internacionalmente para classificar produtos comercializados em todo o mundo. O HS é mantido pela Organização Mundial das Alfândegas (OMA) e é utilizado por mais de 200 países e é o sistema principal usado pela base de dados Comtrade.

Por cada PLP-ano são apresentados os cinco principais produtos exportados para a China e os cinco principais produtos importados da China.

O limite de cinco produtos é configurável.

Por cada combinação país-ano-importação/exportação-produto é apresentado o valor trocado, bem como a percentagem desse
valor no total das importações ou exportações da China com esse país.

Ficheiros produzidos:
* [reports/China_PLP_tops_2003-2023_M_X.xlsx](reports/China_PLP_tops_2003-2023_M_X.xlsx) - Ficheiro Excel com os principais tipos
    de produtos nas trocas comerciais entre a China e os PLP por ano. Por cada país e cada ano disponíveis são apresentados os cinco principais produtos exportados para a China e os cinco principais produtos importados da China. O número de principais produtos é configurável.
* [reports/China_PLP_tops_changes_2003-2023_M_X.txt](reports/China_PLP_tops_changes_2003-2023_M_X.txt) - Ficheiro de texto que
    contém uma análise das variações encontradas nos dados da tabela anterior. As variações detectadas são: alteração da importância
    relativa dos produtos, entrada de novos produtos, saída de produtos, variação do valor de cada produto relativamente ao ano anterior.
    Este relatório procura facilitar a identificação de tendências e mudanças nas trocas comerciais entre a China e os PLP.
* [reports/China_PLP_cmd_detail_2003-2023_M_X.xlsx](reports/China_PLP_cmd_detail_2003-2023_M_X.xlsx)
    Ficheiro Excel com a desagregação dos principais
    produtos nas trocas comerciais entre a China e os PLP por ano. Por cada país e cada ano disponíveis são apresentados os principais produtos exportados para a China e os principais produtos importados da China, desagregados nos códigos HS de nível 6 ou o mais próximo.
    Este relatório permite uma análise mais detalhada dos produtos trocados, uma vez que os códigos HS de nível 6 são mais específicos que os códigos HS de nível 2. Por exemplo
    * 71 = Natural, cultured pearls; precious, semi-precious stones; precious metals, metals clad with precious metal, and articles thereof; imitation jewellery; coin
    * 7102 = Diamonds, whether or not worked, but not mounted or set

O número de principais produtos é configurável. Para cada produto são apresentados os códigos HS, a descrição do produto e o valor trocado.


