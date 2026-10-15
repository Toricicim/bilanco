# Enron Corp. — kaynaklı inceleme

Bilgi kesimi: **2000-03-31 gün sonu (America/New_York)**. Çalışma: `88f8d197-9734-480e-9b46-3d374d963b1b`. Durum: **partial**.

Sonuç etiketi: **inceleme_isareti_var**.

Bu etiket tanımlı kurallara ve aşağıdaki kaynaklara aittir; yatırım güvenliği yüzdesi veya çöküş olasılığı değildir.

## Hesaplanan göstergeler

| Dönem | Gösterge | Değer | Birim |
|---|---|---:|---|
| 1999 | Cari oran | 1.0734 | ratio |
| 1999 | Nakit / kısa vadeli yükümlülük | 0.0426 | ratio |
| 1999 | Uzun vadeli borç / özkaynak | 0.7472 | ratio |
| 1999 | Faaliyet nakdi / net kâr | 1.3751 | ratio |
| 1998 | Cari oran | 0.9715 | ratio |
| 1998 | Nakit / kısa vadeli yükümlülük | 0.0182 | ratio |
| 1998 | Uzun vadeli borç / özkaynak | 1.0438 | ratio |
| 1998 | Faaliyet nakdi / net kâr | 2.3329 | ratio |
| 1999 | Net kâr değişimi | 27.0270 | percent |
| 1999 | Faaliyet nakdi değişimi | -25.1220 | percent |

## Bulgular

### Kâr artarken faaliyet nakdi düşüyor

**İnceleme işareti** — Net kâr değişimi %27.03, faaliyet nakdi değişimi %-25.12. Bu bir inceleme işaretidir; faaliyet nakdinin negatif olduğunu veya hileyi göstermez.

Kaynak konumu: blok `65e1e47225a95e53238972eb`.

```text
Net Income                                    893       703       105
```

Kaynak konumu: blok `f829dae4f8eb234dfba9f0bb`.

```text
Net Cash Provided by Operating
 Activities                                    1,228     1,640       211
```

### 1999: kâr ve faaliyet nakdi

**Dengeleyici / bağlamsal bilgi** — Faaliyet nakdi / net kâr 1.375. Faaliyet nakdi pozitif. Nakit akışı kalemlerinin niteliği ayrıca incelenmeli.

Kaynak konumu: blok `f829dae4f8eb234dfba9f0bb`.

```text
Net Cash Provided by Operating
 Activities                                    1,228     1,640       211
```

Kaynak konumu: blok `65e1e47225a95e53238972eb`.

```text
Net Income                                    893       703       105
```

### 1998: kâr ve faaliyet nakdi

**Dengeleyici / bağlamsal bilgi** — Faaliyet nakdi / net kâr 2.333. Faaliyet nakdi pozitif. Nakit akışı kalemlerinin niteliği ayrıca incelenmeli.

Kaynak konumu: blok `f829dae4f8eb234dfba9f0bb`.

```text
Net Cash Provided by Operating
 Activities                                    1,228     1,640       211
```

Kaynak konumu: blok `65e1e47225a95e53238972eb`.

```text
Net Income                                    893       703       105
```

### 1999: kısa vadeli yükümlülükler

**Dengeleyici / bağlamsal bilgi** — Cari oran 1.073. Dönen varlıkların defter değeri kısa vadeli yükümlülükleri karşılıyor; bu tek başına nakit yeterliliği ölçümü değildir.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current assets                     7,255       5,933
```

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current liabilities                     6,759       6,107
```

### 1998: kısa vadeli yükümlülükler

**İnceleme işareti** — Cari oran 0.972. Dönen varlıkların defter değeri kısa vadeli yükümlülüklerin altında.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current assets                     7,255       5,933
```

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current liabilities                     6,759       6,107
```

### 1999: nakit tamponu

**Dengeleyici / bağlamsal bilgi** — Nakit ve nakit benzerleri / kısa vadeli yükümlülük 0.043. Sektör karşılaştırması yapılmadı.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
  Cash and cash equivalents                 $   288     $   111
```

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current liabilities                     6,759       6,107
```

### 1998: nakit tamponu

**Dengeleyici / bağlamsal bilgi** — Nakit ve nakit benzerleri / kısa vadeli yükümlülük 0.018. Sektör karşılaştırması yapılmadı.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
  Cash and cash equivalents                 $   288     $   111
```

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text
     Total current liabilities                     6,759       6,107
```

### 1999: uzun vadeli borç

**Dengeleyici / bağlamsal bilgi** — Uzun vadeli borç / özkaynak 0.747; toplam borç veya garanti toplamı değildir.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text

Long-Term Debt                                     7,151       7,357
```

Kaynak konumu: blok `94081ed58e3d117d9e5d6ce0`.

```text
     Total shareholders' equity                   9,570       7,048
```

### 1998: uzun vadeli borç

**Dengeleyici / bağlamsal bilgi** — Uzun vadeli borç / özkaynak 1.044; toplam borç veya garanti toplamı değildir.

Kaynak konumu: blok `2c2ee3926a4ecce54fd37f66`.

```text

Long-Term Debt                                     7,151       7,357
```

Kaynak konumu: blok `94081ed58e3d117d9e5d6ce0`.

```text
     Total shareholders' equity                   9,570       7,048
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fa21cf70b51b2cc4c9f36803`.

```text
Enron is a party to certain financial contracts which contain
provisions for early settlement in the event of a significant
market price decline in which Enron's common stock falls below
certain levels (prices ranging from $15.48 to $28.00 per share)
or if the credit ratings for Enron's unsecured, senior long-term
debt obligations fall below investment grade.  The impact of this
early settlement could include the issuance of additional shares
of Enron common stock.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fa21cf70b51b2cc4c9f36803`.

```text
Enron's continued investment grade status is
critical to the success of its wholesale businesses as well as
its ability to maintain adequate liquidity.  Enron's management
believes it will be able to maintain or improve its credit
rating.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fa21cf70b51b2cc4c9f36803`.

```text
Management
believes that the sources of funding described above are
sufficient to meet short- and long-term liquidity needs not met
by cash flows from operations.
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `f650ae7bdd84056f2e757c2b`.

```text
In connection with the Elektro and Wessex financings, which
yielded proceeds of approximately $1.6 billion (see Notes 2 and
9, respectively), Enron committed to cause the sale of Enron
convertible preferred stock, with the number of common shares
issuable upon conversion determined based on future common stock
prices, if certain debt obligations of the related entities
acquiring such interests are defaulted upon, or in certain
events, including, among other things, Enron's credit ratings
falling below specified levels.  If the sale of stock were not
sufficient to retire such obligations, Enron would be liable for
the shortfall.  The obligations will mature in December 2000 and
2001 for Elektro and Wessex, respectively.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
In addition, Enron is
a guarantor on certain liabilities of unconsolidated equity
affiliates and other companies totaling approximately $1,501
million at December 31, 1999, including $427 million related to
EOTT trade obligations.  The EOTT letters of credit and
guarantees of trade obligations are secured by the assets of
EOTT.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
Enron guarantees the performance of certain of its
unconsolidated equity affiliates in connection with letters of
credit issued on behalf of those entities.  At December 31, 1999,
a total of $303 million of such guarantees were outstanding,
including $144 million on behalf of EOTT.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
Enron leases property, operating
facilities and equipment under various operating leases, certain
of which contain renewal and purchase options and residual value
guarantees.  Future commitments related to these items at
December 31, 1999 were $266 million, $88 million, $78 million,
$53 million and $48 million for 2000 through 2004, respectively,
and $370 million for later years. Guarantees under the leases
total $715 million at December 31, 1999.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
Enron has also guaranteed $420 million in lease
obligations for which it has been indemnified by an "Investment
Grade" company.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
Management does not consider it likely that
Enron would be required to perform or otherwise incur any losses
associated with the above guarantees.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
In June 1999, Enron entered into a series of transactions
involving a third party and LJM Cayman, L.P. (LJM).  LJM is a
private investment company which engages in acquiring or
investing in primarily energy-related investments.  A senior
officer of Enron is the managing member of LJM's general partner.
The effect of the transactions was (i) Enron and the third-party
amended certain forward contracts to purchase shares of Enron
common stock, resulting in Enron having forward contracts to
purchase Enron common shares at the market price on that day,
(ii) LJM received 6.8 million shares of Enron common stock
subject to certain restrictions and (iii) Enron received a note
receivable and certain financial instruments hedging an
investment held by Enron.  Enron recorded the assets received and
equity issued at estimated fair value.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
A senior
officer of Enron is the managing member of LJM's general partner.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
In connection with the
transactions, LJM agreed that the Enron officer would have no
pecuniary interest in such Enron common shares and would be
restricted from voting on matters related to such shares.  LJM
repaid the note receivable in December 1999.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21e0a73515600c45fc6f0559`.

```text
In the fourth quarter of 1999, LJM2, which has the
same general partner as LJM, acquired, directly or indirectly,
approximately $360 million of merchant assets and investments
from Enron, on which Enron recognized pre-tax gains of
approximately $16 million.  In December 1999, LJM2 entered into
an agreement to acquire Enron's interests in an unconsolidated
equity affiliate for approximately $34 million.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21e0a73515600c45fc6f0559`.

```text
Additionally,
LJM acquired other assets from Enron for $11 million.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21e0a73515600c45fc6f0559`.

```text
In addition, an officer of Enron
has invested in the limited partner of JEDI and from time to time
acts as agent on behalf of the limited partner's management.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `db8328430cb33390839ce77c`.

```text
At December 31, 1999, Enron
had forward contracts to purchase 22.6 million shares of Enron
Corp. common stock, including approximately 12 million shares
with JEDI, at an average price of $41.52 per share.  Enron may
purchase the shares pursuant to the forward contracts with cash
or an equivalent value of Enron common stock until April 2001.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21e0a73515600c45fc6f0559`.

```text
Management believes that the terms of the transactions with
related parties are representative of terms that would be
negotiated with unrelated third parties.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `acf83b12473af0049be1871c`.

```text
In 1997, Enron and a third-party investor contributed
approximately $579 million and $500 million, respectively, for
interests in Whitewing.  Whitewing purchased 250,000 shares of
Enron Series A Junior Convertible Preferred Stock (Series A
Preferred Stock) from Enron. In March 1999, Whitewing was amended
to allow, among other things, control to be shared equally
between Enron and the third-party investor.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `acf83b12473af0049be1871c`.

```text
In addition, Enron entered
into a Share Settlement Agreement under which Enron could be
obligated, under certain circumstances, to deliver additional
shares of common stock or Series B Preferred Stock to Whitewing
for the amount that the market price of the converted Enron
common shares is less than $28 per share.
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `acf83b12473af0049be1871c`.

```text
Absent certain defaults or other specified
events, Enron has the option to acquire the outside investors'
interests.  If Enron does not acquire the outside investors'
interests before January 2003, or earlier upon certain specified
events, Whitewing will liquidate its assets and dissolve.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21e0a73515600c45fc6f0559`.

```text
In 1999, Whitewing acquired approximately $192 million of
merchant assets from Enron.  Enron recognized no gains or losses
in connection with these transactions.
```

### Denetçi görüşü pasajı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `4bb2bc07cf4cc9bc561bb11d`.

```text
   In our opinion, the financial statements referred to above
present fairly, in all material respects, the financial position
of Enron Corp. and subsidiaries as of December 31, 1999 and 1998,
and the results of their operations, cash flows and changes in
shareholders' equity for each of the three years in the period
ended December 31, 1999, in conformity with accounting principles
generally accepted in the United States.

   As discussed in Note 18 to the consolidated financial
statements, Enron Corp. and subsidiaries changed its method of
accounting for costs of start-up activities and its method of
accounting for certain contracts involved in energy trading and
risk management activities in the first quarter of 1999.




ARTHUR ANDERSEN LLP

Houston, Texas
March 13, 2000
```

### Denetçi görüşü pasajı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `c756285d40211bea05bcd52b`.

```text
We have audited in accordance with generally accepted
auditing standards, the consolidated financial statements of
Enron Corp. and subsidiaries included in this Form 10-K and
have issued our report thereon dated March 13, 2000.  Our
audit was made for the purpose of forming an opinion on the
basic financial statements taken as a whole.  The schedule
listed in Item 14(a)2 is the responsibility of the company's
management and is presented for purposes of complying with
the Securities and Exchange Commission's rules and is not
part of the basic financial statements.  This schedule has
been subjected to the auditing procedures applied in the
audit of the basic financial statements and, in our opinion,
fairly states in all material respects the financial data
required to be set forth therein in relation to the basic
financial statements taken as a whole.





Arthur Andersen LLP

Houston, Texas
March 13, 2000
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `baee897c3ed3fdb3a519b5ec`.

```text
Included in Enron's domestic interstate natural
gas pipeline operations are Northern Natural Gas Company
("Northern"), Transwestern Pipeline Company ("Transwestern")
and Florida Gas Transmission Company ("Florida Gas")
(indirectly 50% owned by Enron).
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `baee897c3ed3fdb3a519b5ec`.

```text
In addition, Enron
holds an interest in Northern Border Partners, L.P., which
owns a 70% interest in the Northern Border Pipeline system.
An Enron subsidiary operates the Northern Border Pipeline
system, which transports gas from Western Canada to delivery
points in the midwestern United States.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `1c70edb5784d854dfded1010`.

```text
An Enron subsidiary
owns a 50% interest in Florida Gas by virtue of its 50%
interest in Citrus Corp., which owns all of the capital
stock of Florida Gas.  Another Enron subsidiary operates the
Florida Gas pipeline.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `1c70edb5784d854dfded1010`.

```text
Northern Border
Partners, L.P., a Delaware limited partnership, owns 70% of
Northern Border Pipeline Company, a Texas general
partnership ("Northern Border").  An Enron subsidiary holds
a 12.4% interest in the limited partnership and serves as
operator of the pipeline.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fe41df3b0ef526938402897e`.

```text
EOTT
Energy Corp. (a wholly-owned subsidiary of Enron) serves as
the general partner of EOTT.  Enron owns a minority interest
in EOTT.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fe41df3b0ef526938402897e`.

```text
Enron's electric utility operations are conducted
through its wholly-owned subsidiary Portland General
Electric Company ("PGE").
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `4b2c20ccfad8e52d5a01134c`.

```text
Enron's intrastate natural gas pipelines include
Houston Pipe Line Company ("HPL"), which owns a 5,269-mile
pipeline in Texas which interconnects with Northern,
Transwestern, Florida Gas and numerous other interstate and
intrastate pipelines.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `4ba4c49ec1e948dac21e7152`.

```text
Enron also owns an interest in Louisiana Resources
Company ("LRC"), which owns a 540-mile intrastate pipeline,
and the Napoleonville natural gas storage facility in
Louisiana, which accesses the LRC pipeline and provides four
Bcf of working capacity.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e2d919b80c966684e6d542b5`.

```text
In connection with a Power Purchase Agreement between
Dabhol Power Company, Enron's 60%-owned subsidiary, and the
Maharashtra State Electricity Board (the "MSEB"), Dabhol
Power Company has constructed Phase I of an electricity
generating power plant south of Mumbai, State of
Maharashtra, India.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `44440ab8ae2dab7f555f270a`.

```text
Enron owns a 35%
interest in Transportadora de Gas del Sur ("TGS") in
Argentina.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `44440ab8ae2dab7f555f270a`.

```text
Enron has a 25% interest in Transredes Transporte de
Hidrocarburos S.A. ("Transredes"), an approximately 3,570-
mile system of natural gas, crude oil and products pipelines
located in Bolivia and connecting Bolivian oil and gas
reserves to major markets in Bolivia.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `da45f32ebebff81786d59ce9`.

```text
Enron has a majority ownership interest in Elektro-
Electricidade e Servicos S.A. ("Elektro").
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `da45f32ebebff81786d59ce9`.

```text
Certain of Enron's operations in the Caribbean area are
conducted through Enron Americas, Inc. and its subsidiary
companies.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `da45f32ebebff81786d59ce9`.

```text
Enron Americas' subsidiary Industrias Ventane,
organized in 1953, operates the leading natural gas liquids
transportation and distribution business in Venezuela.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6bcbaa0c8cc11b172be4f76c`.

```text
The Batangas power project, owned 100% by
Enron, is an approximately 110-megawatt fuel-oil-fired
diesel engine plant located at Pinamucan, Batangas, on Luzon
Island, which began commercial operation in July 1993.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6bcbaa0c8cc11b172be4f76c`.

```text
The
Subic Bay power project, owned 50% by Enron, is an
approximately 116-megawatt fuel-oil-fired diesel engine
plant located at the Subic Bay Freeport complex on Luzon
Island, which began commercial operation in February 1994.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6bcbaa0c8cc11b172be4f76c`.

```text
Enron has a 100% interest in an approximately 160-
megawatt diesel combined-cycle power plant on Hainan Island,
a special economic trade zone off the southeastern coast of
China.  The independent power project is the first such
project developed by a U.S. company in China.  An Enron
affiliate is operator and fuel manager.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `613c6d93a2130ca50ebcbbe1`.

```text
Enron owns a 50% voting interest in
Atlantic Water Trust, which currently owns approximately 67%
of Azurix common stock, with public stockholders owning the
remainder.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `cf70dec3908a4674bf054b22`.

```text
It is not anticipated that Enron will be
required in the near future to expend amounts that are
material in relation to its total capital expenditures
program by reason of environmental laws and regulations, but
inasmuch as such laws and regulations are frequently
changed, Enron is unable to predict the ultimate cost of
compliance.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `16e2d46bbfbfbef7f3219b39`.

```text
Although Enron believes that
its operations are in compliance in all material respects
with all applicable environmental laws and regulations in
the applicable foreign jurisdictions, Enron also believes
that the operations of its projects eventually may be
required to meet standards that are comparable in many
respects to those in effect in the United States and in
countries within the European Community.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `d9ded161fa2e4a6032338f25`.

```text
Enron believes that its operations and facilities are in
general compliance with applicable environmental
regulations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `21a7e2a1daeffdca264fe010`.

```text
However, management
does not believe that any costs incurred in connection with
these sites (either individually or in the aggregate) will
have a material impact on Enron's financial position or
results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `5f73033f857007cb3c01090e`.

```text
Approval of
the Trojan Decommissioning Plan by the NRC and Oregon Energy
Facility Siting Counsel has allowed PGE to commence
decommissioning activities, which are proceeding
satisfactorily and within approved cost estimates.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a42b33c92182b2d3779527fc`.

```text
Enron is of the opinion that it has generally
satisfactory title to its rights-of-way and lands used in
the conduct of its businesses, subject to liens for current
taxes, liens incident to operating agreements and minor
encumbrances, easements and restrictions which do not
materially detract from the value of such property or the
interest of Enron therein or the use of such properties in
such businesses.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `49f3d017c9905c06aee83b7d`.

```text
In 1995, several parties (the Plaintiffs)
filed suit in Harris County District Court in Houston,
Texas, against Intratex Gas Company (Intratex), Houston Pipe
Line Company and Panhandle Gas Company (collectively, the
Enron Defendants), each of which is a wholly-owned
subsidiary of Enron.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e4f042ea718e658388e6ff42`.

```text
San Juan
Gas Company, Inc. (San Juan), an Enron subsidiary, operated
a propane/air distribution system in the vicinity.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `caf764e48672b38bfb696e07`.

```text
Houston Natural Gas Corporation, a
predecessor of Enron Corp., merged with Liquid Carbonic
Industries (LCI) on January 31, 1969.  Liquid Carbonic
Corporation (LCC), a subsidiary of LCI, had title to the
site.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `49f3d017c9905c06aee83b7d`.

```text
Although
no assurances can be given, Enron believes, based on its
experience to date and after considering appropriate
reserves that have been established, that the ultimate
resolution of such items, individually or in the aggregate,
will not have a materially adverse impact on Enron's
financial position or its results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `49f3d017c9905c06aee83b7d`.

```text
The Enron Defendants deny the
Plaintiffs' claims and have asserted various affirmative
defenses, including the statute of limitations.  The Enron
Defendants believe that they have strong legal and factual
defenses, and intend to vigorously contest the claims.
Although no assurances can be given, Enron believes that the
ultimate resolution of these matters will not have a
materially adverse effect on its financial position or
results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e4f042ea718e658388e6ff42`.

```text
Although
San Juan did not provide service to the building, the
National Transportation Safety Board (NTSB) concluded that
the probable cause of the incident was propane leaking from
San Juan's distribution system.  San Juan and Enron strongly
disagree.  The NTSB found no path of migration of propane
from San Juan's system to the building and no forensic
evidence that propane fueled the explosion.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e4f042ea718e658388e6ff42`.

```text
Enron, San Juan and its
affiliates are vigorously contesting the claims.  Although
no assurances can be given, Enron believes that the ultimate
resolution of these matters will not have a materially
adverse effect on its financial position or results of
operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `20d1a708c65b63625939a950`.

```text
Enron cannot predict the outcome of these
actions.  Additionally, due to uncertainties in the
regulatory process, management cannot predict, with
certainty, what ultimate rate-making action the OPUC will
take regarding PGE's recovery of a rate of return on its
Trojan investment.  Although no assurances can be given,
Enron believes that the ultimate resolution of these matters
will not have a material adverse effect on its financial
position or results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `20d1a708c65b63625939a950`.

```text
The EPA alleges that hazardous
substances were released to the environment during the
period in which Enron's predecessor owned the site, and that
Enron's predecessor assumed the liabilities of the company
that operated the plant.  Enron contests these allegations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `caf764e48672b38bfb696e07`.

```text
Although
Enron does not admit liability with respect to any costs at
this site, it agreed to cooperate with the EPA and other
potentially responsible parties to undertake the work
contemplated by EPA's Order.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `caf764e48672b38bfb696e07`.

```text
However,
based upon the amounts claimed and the nature and volume of
materials sent to sites at which Enron has an interest,
management does not believe that any potential costs
incurred in connection with these notices and third party
claims, either taken individually or in the aggregate, will
have a material impact on Enron's financial position or
results of operations.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `2bb641483f16e9559e9412c0`.

```text
The Gas Pipeline Group
includes Enron's interstate natural gas pipelines, primarily
Northern Natural Gas Company (Northern), Transwestern Pipeline
Company (Transwestern), Enron's 50% interest in Florida Gas
Transmission Company (Florida Gas) and Enron's interests in
Northern Border Pipeline and EOTT Energy Partners, L.P. (EOTT).
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `f683733c9605af0c35089e40`.

```text
Florida Gas and
    Northern Border Pipeline are unconsolidated equity affiliates.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `c52b8c529205c782b94b8068`.

```text
Included in 1999 was interest income earned in connection with
the financing of an acquisition by EOTT, while the 1998 amount
included gains of $21 million recognized from the sale of an
interest in an equity investment, substantially offset by charges
related to litigation.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `c52b8c529205c782b94b8068`.

```text
The 1998 results were impacted by a warmer than normal winter
and the transfer of the majority of Portland General's
electricity wholesale business to the Enron Wholesale segment,
partially offset by an increase in sales to retail customers.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `fa21cf70b51b2cc4c9f36803`.

```text
Certain of the credit agreements
contain prefunding covenants.  However, such covenants are not
expected to restrict Enron's access to funds under these
agreements.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `511d856ad61d0f2e481d1125`.

```text
The Year 2000 problem has caused no material disruption to
Enron's mission-critical facilities or operations, and resulted
in no material costs.  Enron will remain vigilant for Year 2000
related problems that may yet occur due to hidden defects in
computer hardware or software at Enron or Enron's mission-
critical external entities.  Enron anticipates that the Year 2000
problem will not create material disruptions to its mission-
critical facilities or operations, and will not create material
costs.
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `2a860568470890c7a03f97b8`.

```text
Enron's ability to access the capital markets and
equity markets during the periods covered by the forward-looking
statements, which will depend on general market conditions and
Enron's ability to maintain or increase the credit ratings for
its unsecured senior long-term debt obligations.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.24  -      Split Dollar Life Insurance Agreement
               between Enron and the KLL and LPL Family
               Partnership, Ltd., dated April 22, 1994
               (Exhibit 10.17 to Enron Form 10-K for 1994).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.25  -      Employment Agreement between Enron Corp.
               and Kenneth L. Lay, executed December 18, 1996
               (Exhibit 10.25 to Enron Form 10-K for 1996).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
10.26  -      First Amendment to Employment Agreement
               between Enron Corp. and Kenneth L. Lay, dated
               February 7, 2000.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.27  -      Consulting Services Agreement between
               Enron and John A. Urquhart dated August 1,
               1991 (Exhibit 10.23 to Enron Form 10-K for
               1991).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.28  -      First Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart,
               dated August 27, 1992 (Exhibit 10.25 to Enron
               Form 10-K for 1992).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.29  -      Second and Third Amendments to Consulting
               Services Agreement between Enron and John A.
               Urquhart, dated November 24, 1992 and February
               26, 1993, respectively (Exhibit 10.26 to Enron
               Form 10-K for 1992).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.30  -      Fourth Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart
               dated as of May 9, 1994 (Exhibit 10.35 to
               Enron Form 10-K for 1995).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.31 -       Fifth Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart
               (Exhibit 10.36 to Enron Form 10-K for 1995).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.32  -      Sixth Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart
               (Exhibit 10.37 to Enron Form 10-K for 1995).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.33  -      Seventh Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart,
               dated October 27, 1997 (Exhibit 10.27 to Enron
               Form 10-K for 1997).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `bd59fe5baababc4bf80f798e`.

```text
*10.34  -      Eighth Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart,
               dated May 27, 1998 (Exhibit 10.28 to Enron
               Form 10-K for 1998).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.35  -      Ninth Amendment to Consulting Services
               Agreement between Enron and John A. Urquhart,
               dated December 31, 1998 (Exhibit 10.29 to
               Enron Form 10-K for 1998).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
10.36  -      Tenth Amendment to Consulting Services
               Agreement between John A. Urquhart and Enron
               Corp. dated January 1, 2000.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.43  -      Employment Agreement between Enron
               Capital Trade & Resources Corp. and Jeffrey K.
               Skilling, dated January 1, 1996 (Exhibit 10.63
               to Enron Form 10-K for 1996).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.44  -      First Amendment effective January 1,
               1997, by and among Enron Corp., Enron Capital
               & Trade Resources Corp., and Jeffrey K.
               Skilling, amending Employment Agreement
               between Enron Capital & Trade Resources Corp.
               and Jeffrey K. Skilling dated January 1, 1996
               (Exhibit 10.64 to Enron Form 10-K for 1996).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.45  -      Split Dollar Agreement between Enron and
               Jeffrey K. Skilling dated May 23, 1997
               (Exhibit 10.41 to Enron Form 10-K for 1997).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.46  -      Second Amendment effective October 13,
               1997, to Employment Agreement between Enron
               Corp. and Jeffrey K. Skilling (Exhibit 10.42
               to Enron Form 10-K for 1997).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
*10.47  -      Loan Agreement effective October 13,
               1997, between Enron Corp. and Jeffrey K.
               Skilling (Exhibit 10.43 to Enron Form 10-K for
               1997).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `e0a8992f10f65dd938b2e536`.

```text
10.48  -      Third Amendment to Employment Agreement
               between Enron Corp. and Jeffrey K. Skilling,
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
*10.49  -      Employment Agreement dated July 20, 1996
               (effective July 1, 1997) between Enron and Ken
               L. Harrison (Exhibit 10.1 to Post-Effective
               Amendment No. 1 to Enron's Registration
               Statement on Form S-4, File No. 333-13791).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
*10.50  -      Executive Employment Agreement between
               Enron Corp. and Rebecca P. Mark, effective May
               4, 1998 (Exhibit 10.41 to Enron Form 10-K for
               1998).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
10.51  -      First Amendment to Executive Employment
               Agreement by and between Enron Corp., Azurix
               Corp. and Rebecca P. Mark, dated February 1,
               1999.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
*10.52  -      Executive Employment Agreement between
               Enron Corp. and Joseph W. Sutton, effective
               June 23, 1998 (Exhibit 10.42 to Enron Form
               10-K for 1998).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
10.53  -      Amendment to Executive Employment
               Agreement between Enron Corp. and Joseph W.
               Sutton, dated May 5, 1999.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
10.54  -      Second Amendment to Executive Employment
               Agreement between Enron Corp. and Joseph W.
               Sutton, dated July 1, 1999.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
*10.55  -      Executive Employment Agreement between
               Enron Operations Corp. and Stanley C. Horton,
               dated as of October 1, 1999 (Exhibit 10.45 to
               Enron Form 10-K for 1997).
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
10.56  -      First Amendment to Executive Employment
               Agreement by and between Enron Operations
               Corp., Enron Corp. and Stanley C. Horton,
               dated December 27, 1999.
```

### Yönetici–karşı taraf ilişkisi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a27829f305115f9a6c30df93`.

```text
10.57  -      Executive Employment Agreement between
               Enron Corp. and Mark A. Frevert, effective
               June 1, 1998.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `cc5dbf4fd28b65542ceb24dd`.

```text
On August 16, 1999, Enron exchanged approximately 62.3 million
shares (approximately 75%) of the Enron Oil & Gas Company (EOG)
common stock it held for all of the stock of EOGI-India, Inc., a
subsidiary of EOG.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `cc5dbf4fd28b65542ceb24dd`.

```text
In August 1998, Enron, through a wholly-owned subsidiary,
completed the acquisition of a controlling interest in Elektro
Eletricidade e Servicos S.A. (Elektro), an electricity
distributor in Brazil, for approximately $1.3 billion.  Enron's
interest in Elektro is held by Jacare Electrical Distribution
Trust (Jacare) and was initially accounted for using the equity
method based on temporary control.  In December 1998, Enron
financially closed the Elektro financial restructuring, reducing
its interest in Jacare to 51%.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `cc5dbf4fd28b65542ceb24dd`.

```text
In November 1997, Enron acquired the minority interest in
Enron Global Power & Pipelines L.L.C. (EPP) in a stock-for-stock
transaction.  Enron issued approximately 23 million common shares
in exchange for the EPP shares held by the minority shareholders.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `59b4a7debb14b5f1948036e5`.

```text
On November 8, 1999, Enron announced that it had entered into
an agreement to sell Enron's wholly-owned electric utility
subsidiary, Portland General Electric Company (PGE), to Sierra
Pacific Resources for $2.1 billion, comprised of $2.02 billion in
cash and the assumption of Enron's approximately $80 million
merger payment obligation.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a4ca8a7d1cab7b6f5c23a174`.

```text
Enron maintains credit
policies with regard to its counterparties that management
believes significantly minimize overall credit risk.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `8f481de2e810bb9dcaab939b`.

```text
(a) "Investment Grade" is primarily determined using publicly
    available credit ratings along with consideration of
    collateral, which encompass standby letters of credit, parent
    company guarantees and property interests, including oil and
    gas reserves.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `8f481de2e810bb9dcaab939b`.

```text
Based on Enron's
policies, its exposures and its credit and other reserves, Enron
does not anticipate a materially adverse effect on financial
position or results of operations as a result of counterparty
nonperformance.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `8327b9fdd712bde6b9e0174f`.

```text
However, Enron's management believes that its
portfolio of receivables is well diversified and that such
diversification minimizes any potential credit risk.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `8327b9fdd712bde6b9e0174f`.

```text
Guarantees of liabilities of unconsolidated entities and
residual value guarantees have no carrying value and fair values
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `ded6246868cde780769c38b7`.

```text
Certain credit
facilities contain covenants which must be met to borrow funds.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `ded6246868cde780769c38b7`.

```text
Such debt covenants are not anticipated to materially restrict
Enron's ability to borrow funds under such facilities.
```

### Kredi notu / temerrüt koşulu adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a6af924db2aa87d711165852`.

```text
Absent certain defaults or other specified events, Enron has
the option to acquire the minority holders' interests in these
partnerships.  If Enron does not acquire the minority holders'
interests before December 2004 through May 2009, or earlier upon
certain specified events, the entities will liquidate their
assets and dissolve.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a9a90e89de84cd2576128cfd`.

```text
(a) Includes $327 million and $196 million receivable from
    Enron and $84 million and $296 million payable to Enron at
    December 31, 1999 and 1998, respectively.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `a9a90e89de84cd2576128cfd`.

```text
(a) Enron recognized revenues from transactions with
    unconsolidated equity affiliates of $161 million in 1999, $142
    million in 1998 and $219 million in 1997.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `acf83b12473af0049be1871c`.

```text
From time to time, Enron has entered into various
administrative service, management, construction, supply and
operating agreements with its unconsolidated equity affiliates.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `acf83b12473af0049be1871c`.

```text
Enron's management believes that its existing agreements and
transactions are reasonable compared to those which could have
been obtained from third parties.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `f650ae7bdd84056f2e757c2b`.

```text
If the sale of stock were not
sufficient to retire such obligations, Enron would be liable for
the shortfall.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `111cfea7a85f7d2cc9a07cdf`.

```text
Enron believes, based upon its experience to date and after
considering appropriate reserves that have been established, that
the ultimate resolution of pending regulatory matters will not
have a material impact on Enron's financial position or results
of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `59648ad285822d691ec3e409`.

```text
Although no
assurances can be given, Enron believes, based on its experience
to date and after considering appropriate reserves that have been
established, that the ultimate resolution of such items,
individually or in the aggregate, will not have a material
adverse impact on Enron's financial position or its results of
operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `59648ad285822d691ec3e409`.

```text
The Enron Defendants deny the Plaintiffs' claims
and have asserted various affirmative defenses, including the
statute of limitations.  The Enron Defendants believe that they
have strong legal and factual defenses, and intend to vigorously
contest the claims.  Although no assurances can be given, Enron
believes that the ultimate resolution of these matters will not
have a material adverse effect on its financial position or
results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `59648ad285822d691ec3e409`.

```text
Although San Juan did not
provide service to the building, the National Transportation
Safety Board (NTSB) concluded that the probable cause of the
incident was propane leaking from San Juan's distribution system.
San Juan and Enron strongly disagree.  The NTSB found no path of
migration of propane from San Juan's system to the building and
no forensic evidence that propane fueled the explosion.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `59648ad285822d691ec3e409`.

```text
Enron, San Juan and its affiliates are vigorously
contesting the claims.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `57741113a00a1fcbfb8944f1`.

```text
Enron cannot predict the outcome of these actions.
Additionally, due to uncertainties in the regulatory process,
management cannot predict, with certainty, what ultimate rate-
making action the OPUC will take regarding PGE's recovery of a
rate of return on its Trojan investment.  Although no assurances
can be given, Enron believes that the ultimate resolution of
these matters will not have a material adverse effect on its
financial position or results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `57741113a00a1fcbfb8944f1`.

```text
The
implementation of the Clean Air Act Amendments is expected to
result in increased operating expenses.  These increased
operating expenses are not expected to have a material impact on
Enron's financial position or results of operations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `603acf557e963f0f89bc80be`.

```text
The EPA
alleges that hazardous substances were released to the
environment during the period in which Enron's predecessor owned
the site, and that Enron's predecessor assumed the liabilities of
the company that operated the plant.  Enron contests these
allegations.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `603acf557e963f0f89bc80be`.

```text
Enron does not expect to incur material expenditures
in connection with this site.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `603acf557e963f0f89bc80be`.

```text
Although Enron does not
admit liability with respect to any costs at this site, it agreed
to cooperate with the EPA and other potentially responsible
parties to undertake the work contemplated by the EPA's Order.
```

### Şirketin dengeleyici açıklaması

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `603acf557e963f0f89bc80be`.

```text
Enron
does not expect to incur material expenditures in connection with
soil and groundwater remediation.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `603acf557e963f0f89bc80be`.

```text
Enron has firm
transportation agreements with various joint venture pipelines.
Under these agreements, Enron must make specified minimum
payments each month.  At December 31, 1999, the estimated
aggregate amounts of such required future payments were $65
million, $68 million, $69 million, $70 million and $74 million
for 2000 through 2004, respectively, and $515 million for later
years.
```

### Garanti veya taahhüt adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
Enron has assigned firm transportation contracts
with two of its joint ventures to third parties and guaranteed
minimum payments under the contracts averaging approximately $36
million annually through 2001 and $3 million in 2002.
```

### İlişkili taraf işlemi adayı

**Anlam doğrulaması gerekli** — Alıntı belirtilen kaynak konumuyla eşleşiyor. AI'ın ilişki/tür yorumunun anlam doğruluğu bağımsız olarak onaylanmadı; kesinleşmiş hile veya risk sonucu değildir.

Kaynak konumu: blok `6f920069e660e4374a333558`.

```text
In November 1999, a subsidiary of Enron made a contribution
leaseback of assets in return for a preferred interest in an
unconsolidated equity affiliate of Enron.  As a result of this
transaction, Enron has net future obligations of $5 million each
year for 2000 through 2004 and $49 million thereafter.
```

## Kaynaklar

- https://www.sec.gov/Archives/edgar/data/1024401/000102440100000002/0001024401-00-000002.txt
  - Yayın: 2000-03-31; edinim: 2026-10-15T14:43:39.031940+00:00; önbellek: True.
  - SHA-256: `79712897680446c518182c56755b3f67341368dbeb492027ac08ae3f2b30ed00`.
  - Özgün SEC dosyalaması.
  - Yayın kanıtı: SEC SGML header; https://www.sec.gov/Archives/edgar/data/1024401/000102440100000002/0001024401-00-000002.txt; sha256=79712897680446c518182c56755b3f67341368dbeb492027ac08ae3f2b30ed00

## Eksikler ve sınırlar

- Modelin Enron hakkındaki eğitim bilgisi silinemez; bu çalışma tamamen kör bir tarihsel tahmin testi değildir.
- Kaynak eşleşmesi, şirketin kendi beyanının bağımsız olarak doğru olduğunu göstermez.
- AI ilişki adaylarında alıntı doğrulaması ile anlam doğrulaması ayrıdır; adaylar kesinleşmiş risk veya hile tespiti sayılmaz.
- Bu sürümde sektör/emsal karşılaştırması, fiyat tahmini ve kalibre edilmiş risk olasılığı yok.
- 1 çıkarım/satır reddedildi; ayrıntılar JSON çıktısında.

## Çalışma süreleri

- document_reading: 0.013 saniye
- source_acquisition: 0.015 saniye
- source_discovery: 12.136 saniye
- table_extraction: 0.070 saniye
- ai_extraction: 286.389 saniye
- narrative: 17.262 saniye
- total: 315.881 saniye
- http_requests: 0.000 saniye
