"""Translations of the form score (2026-11-28): python3 tools/i18n/parts_form.py.
Machine-style translations like the rest, pending native-speaker review."""
import json

K = [
    "Counted on squats, push-ups and lunges only. The camera checks a few simple rules on each rep; it does not judge your technique beyond them.",
    "Form",
    "Form check",
    "Latest {0}%",
    "reps with nothing flagged",
    "{0} of {1} reps with nothing flagged",
    "{0} of {1} with nothing flagged",
]

T = {
"bg": ["Отчита се само при клекове, лицеви опори и напади. Камерата проверява няколко прости правила при всяко повторение; тя не оценява техниката ти отвъд тях.", "Форма", "Проверка на формата", "Последно {0}%", "повторения без отбелязано", "{0} от {1} повторения без отбелязано", "{0} от {1} без отбелязано"],
"cs": ["Počítá se jen u dřepů, kliků a výpadů. Kamera u každého opakování kontroluje několik jednoduchých pravidel; tvou techniku nad jejich rámec nehodnotí.", "Forma", "Kontrola formy", "Naposledy {0} %", "opakování bez upozornění", "{0} z {1} opakování bez upozornění", "{0} z {1} bez upozornění"],
"da": ["Tælles kun på squats, armstrækninger og udfald. Kameraet tjekker nogle få enkle regler ved hver gentagelse; det vurderer ikke din teknik ud over dem.", "Form", "Formtjek", "Seneste {0} %", "gentagelser uden markering", "{0} af {1} gentagelser uden markering", "{0} af {1} uden markering"],
"de": ["Nur bei Kniebeugen, Liegestützen und Ausfallschritten gezählt. Die Kamera prüft bei jeder Wiederholung ein paar einfache Regeln; deine Technik darüber hinaus beurteilt sie nicht.", "Form", "Form-Check", "Zuletzt {0} %", "Wiederholungen ohne Hinweis", "{0} von {1} Wiederholungen ohne Hinweis", "{0} von {1} ohne Hinweis"],
"el": ["Μετράει μόνο σε καθίσματα, κάμψεις και προβολές. Η κάμερα ελέγχει λίγους απλούς κανόνες σε κάθε επανάληψη· δεν κρίνει την τεχνική σου πέρα από αυτούς.", "Φόρμα", "Έλεγχος φόρμας", "Τελευταία {0}%", "επαναλήψεις χωρίς επισήμανση", "{0} από {1} επαναλήψεις χωρίς επισήμανση", "{0} από {1} χωρίς επισήμανση"],
"es": ["Solo cuenta en sentadillas, flexiones y zancadas. La cámara comprueba unas pocas reglas sencillas en cada repetición; no juzga tu técnica más allá de ellas.", "Técnica", "Control de técnica", "Último {0} %", "repeticiones sin aviso", "{0} de {1} repeticiones sin aviso", "{0} de {1} sin aviso"],
"et": ["Arvestatakse ainult kükkide, kätekõverduste ja väljaastete puhul. Kaamera kontrollib igal kordusel mõnda lihtsat reeglit; sinu tehnikat neist kaugemale ta ei hinda.", "Tehnika", "Tehnika kontroll", "Viimati {0}%", "kordust ilma märkuseta", "{0}/{1} kordust ilma märkuseta", "{0}/{1} ilma märkuseta"],
"fi": ["Lasketaan vain kyykyissä, punnerruksissa ja askelkyykyissä. Kamera tarkistaa jokaisesta toistosta muutaman yksinkertaisen säännön; se ei arvioi tekniikkaasi niiden ulkopuolelta.", "Tekniikka", "Tekniikan tarkistus", "Viimeksi {0} %", "toistoa ilman huomautusta", "{0}/{1} toistoa ilman huomautusta", "{0}/{1} ilman huomautusta"],
"fr": ["Compté uniquement sur les squats, les pompes et les fentes. La caméra vérifie quelques règles simples à chaque répétition ; elle ne juge pas ta technique au-delà.", "Forme", "Contrôle de la forme", "Dernier {0} %", "répétitions sans signalement", "{0} sur {1} répétitions sans signalement", "{0} sur {1} sans signalement"],
"ga": ["Ní chomhairtear é ach ar scuait, brú suas agus sáfacha. Seiceálann an ceamara cúpla riail shimplí ar gach athrá; ní mheasann sé do theicníc lasmuigh díobh sin.", "Foirm", "Seiceáil foirme", "Is déanaí {0}%", "athráite gan aon rud marcáilte", "{0} as {1} athrá gan aon rud marcáilte", "{0} as {1} gan aon rud marcáilte"],
"hr": ["Broji se samo kod čučnjeva, sklekova i iskoraka. Kamera pri svakom ponavljanju provjerava nekoliko jednostavnih pravila; tvoju tehniku izvan njih ne ocjenjuje.", "Forma", "Provjera forme", "Zadnje {0} %", "ponavljanja bez napomene", "{0} od {1} ponavljanja bez napomene", "{0} od {1} bez napomene"],
"hu": ["Csak guggolásnál, fekvőtámasznál és kitörésnél számít. A kamera minden ismétlésnél néhány egyszerű szabályt ellenőriz; a technikádat ezeken túl nem ítéli meg.", "Forma", "Formaellenőrzés", "Legutóbb {0}%", "ismétlés jelzés nélkül", "{0} / {1} ismétlés jelzés nélkül", "{0} / {1} jelzés nélkül"],
"it": ["Conta solo su squat, piegamenti e affondi. La fotocamera controlla poche regole semplici a ogni ripetizione; non giudica la tua tecnica oltre a queste.", "Forma", "Controllo della forma", "Ultimo {0}%", "ripetizioni senza segnalazioni", "{0} di {1} ripetizioni senza segnalazioni", "{0} di {1} senza segnalazioni"],
"lt": ["Skaičiuojama tik pritūpimams, atsispaudimams ir įtūpstams. Kamera kiekviename pakartojime tikrina kelias paprastas taisykles; tavo technikos už jų ribų ji nevertina.", "Technika", "Technikos patikra", "Paskutinį kartą {0} %", "pakartojimų be pastabų", "{0} iš {1} pakartojimų be pastabų", "{0} iš {1} be pastabų"],
"lv": ["Skaita tikai pietupieniem, atspiešanās un izklupieniem. Kamera katrā atkārtojumā pārbauda dažus vienkāršus noteikumus; tavu tehniku ārpus tiem tā nevērtē.", "Tehnika", "Tehnikas pārbaude", "Pēdējoreiz {0}%", "atkārtojumi bez atzīmes", "{0} no {1} atkārtojumiem bez atzīmes", "{0} no {1} bez atzīmes"],
"mt": ["Jgħodd biss fuq squats, push-ups u lunges. Il-kamera tiċċekkja ftit regoli sempliċi f'kull ripetizzjoni; ma tiġġudikax it-teknika tiegħek lil hinn minnhom.", "Forma", "Kontroll tal-forma", "L-aħħar {0}%", "ripetizzjonijiet mingħajr xejn immarkat", "{0} minn {1} ripetizzjonijiet mingħajr xejn immarkat", "{0} minn {1} mingħajr xejn immarkat"],
"nl": ["Alleen geteld bij squats, push-ups en lunges. De camera controleert bij elke herhaling een paar eenvoudige regels; je techniek daarbuiten beoordeelt hij niet.", "Vorm", "Vormcheck", "Laatst {0}%", "herhalingen zonder melding", "{0} van {1} herhalingen zonder melding", "{0} van {1} zonder melding"],
"pl": ["Liczone tylko przy przysiadach, pompkach i wykrokach. Kamera sprawdza przy każdym powtórzeniu kilka prostych zasad; nie ocenia twojej techniki poza nimi.", "Technika", "Kontrola techniki", "Ostatnio {0}%", "powtórzeń bez uwag", "{0} z {1} powtórzeń bez uwag", "{0} z {1} bez uwag"],
"pt": ["Conta apenas em agachamentos, flexões e lunges. A câmara verifica algumas regras simples em cada repetição; não avalia a tua técnica para além delas.", "Forma", "Verificação da forma", "Último {0}%", "repetições sem alertas", "{0} de {1} repetições sem alertas", "{0} de {1} sem alertas"],
"ro": ["Se numără doar la genuflexiuni, flotări și fandări. Camera verifică câteva reguli simple la fiecare repetare; nu îți judecă tehnica dincolo de ele.", "Formă", "Verificarea formei", "Ultima dată {0}%", "repetări fără semnalări", "{0} din {1} repetări fără semnalări", "{0} din {1} fără semnalări"],
"sk": ["Počíta sa len pri drepoch, klikoch a výpadoch. Kamera pri každom opakovaní kontroluje niekoľko jednoduchých pravidiel; tvoju techniku nad ich rámec nehodnotí.", "Forma", "Kontrola formy", "Naposledy {0} %", "opakovaní bez upozornenia", "{0} z {1} opakovaní bez upozornenia", "{0} z {1} bez upozornenia"],
"sl": ["Šteje se le pri počepih, sklecah in izpadnih korakih. Kamera pri vsaki ponovitvi preveri nekaj preprostih pravil; tvoje tehnike zunaj njih ne ocenjuje.", "Oblika", "Preverjanje oblike", "Zadnjič {0} %", "ponovitev brez opozorila", "{0} od {1} ponovitev brez opozorila", "{0} od {1} brez opozorila"],
"sv": ["Räknas bara på knäböj, armhävningar och utfall. Kameran kontrollerar några enkla regler vid varje repetition; den bedömer inte din teknik utöver dem.", "Teknik", "Teknikkoll", "Senast {0} %", "repetitioner utan anmärkning", "{0} av {1} repetitioner utan anmärkning", "{0} av {1} utan anmärkning"],
}

if __name__ == "__main__":
    import glob, os
    SRC = json.load(open("tools/i18n/source.json", encoding="utf-8"))
    for p in sorted(glob.glob("app/src/main/assets/i18n/*.json")):
        lang = os.path.basename(p)[:-5]
        rows = T[lang]
        assert len(rows) == len(K), (lang, len(rows))
        t = json.load(open(p, encoding="utf-8"))
        t.update(dict(zip(K, rows)))
        out = {s: t[s] for s in SRC if s in t and str(t[s]).strip()}
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(lang, len(out), "of", len(SRC))
