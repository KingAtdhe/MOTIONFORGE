"""Batch 10 guided-lesson limitation lines: two shared sentences plus a framing sentence.
The framing sentences "Face the phone with your whole body in view." and "Stand side-on to the
phone with your whole body in view." are already translated; the other two are new here.
Run: python3 tools/i18n/parts_batch10c.py"""
import json, glob, os

HEAD = "The camera does not assess this move yet. Follow the demonstration; the timer guides you."
FRAMES = ["Face the phone with your whole body in view.",
          "Stand side-on to the phone with your whole body in view.",
          "Face the phone or stand at a slight angle, with your upper body in view.",
          "Put the phone at floor level, side-on, with your whole body in view."]

# lang: (head, upper-body framing, floor framing)
T = {
"bg": ("Камерата още не оценява това движение. Следвай демонстрацията; таймерът те води.",
       "Застани с лице към телефона или леко под ъгъл, така че горната част на тялото ти да се вижда.",
       "Постави телефона на нивото на пода, отстрани, така че цялото ти тяло да се вижда."),
"cs": ("Kamera tento cvik zatím nehodnotí. Sleduj ukázku; časovač tě vede.",
       "Stůj čelem k telefonu nebo mírně šikmo, s horní částí těla v záběru.",
       "Polož telefon na úroveň podlahy, z boku, s celým tělem v záběru."),
"da": ("Kameraet vurderer ikke denne øvelse endnu. Følg demonstrationen; timeren guider dig.",
       "Stå med front mod telefonen eller lidt på skrå, med overkroppen i billedet.",
       "Stil telefonen i gulvhøjde, fra siden, med hele kroppen i billedet."),
"de": ("Die Kamera bewertet diese Übung noch nicht. Folge der Vorführung; der Timer führt dich.",
       "Stell dich frontal oder leicht schräg zum Handy, mit dem Oberkörper im Bild.",
       "Stell das Handy auf Bodenhöhe seitlich auf, mit dem ganzen Körper im Bild."),
"el": ("Η κάμερα δεν αξιολογεί ακόμη αυτή την κίνηση. Ακολούθησε την επίδειξη· σε καθοδηγεί το χρονόμετρο.",
       "Στάσου μπροστά στο τηλέφωνο ή με μικρή γωνία, με το πάνω μέρος του σώματος στο κάδρο.",
       "Βάλε το τηλέφωνο στο ύψος του πατώματος, στο πλάι, με όλο το σώμα στο κάδρο."),
"es": ("La cámara todavía no evalúa este movimiento. Sigue la demostración; el temporizador te guía.",
       "Ponte de frente al móvil o ligeramente en ángulo, con la parte superior del cuerpo a la vista.",
       "Pon el móvil a la altura del suelo, de lado, con todo el cuerpo a la vista."),
"et": ("Kaamera seda liigutust veel ei hinda. Järgi näidist; taimer juhendab sind.",
       "Seisa telefoni poole näoga või kergelt nurga all, ülakeha kaadris.",
       "Pane telefon põranda kõrgusele, küljelt, kogu keha kaadris."),
"fi": ("Kamera ei vielä arvioi tätä liikettä. Seuraa näytöstä; ajastin ohjaa sinua.",
       "Seiso kasvot puhelimeen päin tai hieman vinottain, ylävartalo kuvassa.",
       "Aseta puhelin lattian tasolle sivulle, koko vartalo kuvassa."),
"fr": ("La caméra n'évalue pas encore ce mouvement. Suis la démonstration ; le minuteur te guide.",
       "Place-toi face au téléphone ou légèrement de biais, le haut du corps dans le cadre.",
       "Pose le téléphone au niveau du sol, de profil, le corps entier dans le cadre."),
"ga": ("Ní mheasann an ceamara an ghluaiseacht seo fós. Lean an taispeántas; treoraíonn an t-amadóir thú.",
       "Seas os comhair an fhóin nó ar uillinn bheag, le barr do choirp le feiceáil.",
       "Cuir an fón ar leibhéal an urláir, ón taobh, le do chorp ar fad le feiceáil."),
"hr": ("Kamera još ne ocjenjuje ovaj pokret. Prati demonstraciju; mjerač vremena te vodi.",
       "Stani licem prema mobitelu ili malo ukoso, s gornjim dijelom tijela u kadru.",
       "Stavi mobitel u razinu poda, sa strane, s cijelim tijelom u kadru."),
"hu": ("A kamera ezt a mozdulatot még nem értékeli. Kövesd a bemutatót; az időzítő vezet.",
       "Állj szemben a telefonnal vagy kissé ferdén, hogy a felsőtested látsszon.",
       "Tedd a telefont padlószintre, oldalról, hogy az egész tested látsszon."),
"it": ("La fotocamera non valuta ancora questo movimento. Segui la dimostrazione; il timer ti guida.",
       "Mettiti di fronte al telefono o leggermente di sbieco, con la parte superiore del corpo inquadrata.",
       "Metti il telefono a livello del pavimento, di lato, con tutto il corpo inquadrato."),
"lt": ("Kamera šio judesio dar nevertina. Sek demonstraciją; laikmatis tave veda.",
       "Stovėk veidu į telefoną arba šiek tiek kampu, kad matytųsi viršutinė kūno dalis.",
       "Padėk telefoną grindų lygyje, iš šono, kad matytųsi visas kūnas."),
"lv": ("Kamera šo kustību vēl nevērtē. Seko demonstrācijai; taimeris tevi vada.",
       "Stāvi ar seju pret telefonu vai nedaudz slīpi, lai redzama ķermeņa augšdaļa.",
       "Novieto telefonu grīdas līmenī, no sāniem, lai redzams viss ķermenis."),
"mt": ("Il-kamera għadha ma tivvalutax dan il-moviment. Segwi d-dimostrazzjoni; it-timer jiggwidak.",
       "Iffaċċja t-telefon jew oqgħod ftit mal-ġenb, bil-parti ta' fuq ta' ġismek tidher.",
       "Poġġi t-telefon fil-livell tal-art, mal-ġenb, b'ġismek kollu jidher."),
"nl": ("De camera beoordeelt deze beweging nog niet. Volg de demonstratie; de timer begeleidt je.",
       "Sta met je gezicht naar de telefoon of iets schuin, met je bovenlichaam in beeld.",
       "Zet de telefoon op vloerhoogte, van opzij, met je hele lichaam in beeld."),
"pl": ("Kamera jeszcze nie ocenia tego ruchu. Podążaj za pokazem; minutnik cię prowadzi.",
       "Stań przodem do telefonu lub lekko ukosem, z górną częścią ciała w kadrze.",
       "Postaw telefon na poziomie podłogi, z boku, z całym ciałem w kadrze."),
"pt": ("A câmara ainda não avalia este movimento. Segue a demonstração; o temporizador guia-te.",
       "Fica de frente para o telemóvel ou ligeiramente de lado, com a parte de cima do corpo à vista.",
       "Põe o telemóvel ao nível do chão, de lado, com o corpo inteiro à vista."),
"ro": ("Camera nu evaluează încă această mișcare. Urmează demonstrația; cronometrul te ghidează.",
       "Stai cu fața spre telefon sau ușor în unghi, cu partea de sus a corpului în cadru.",
       "Pune telefonul la nivelul podelei, lateral, cu tot corpul în cadru."),
"sk": ("Kamera tento cvik zatiaľ nehodnotí. Sleduj ukážku; časovač ťa vedie.",
       "Stoj čelom k telefónu alebo mierne šikmo, s hornou časťou tela v zábere.",
       "Polož telefón na úroveň podlahy, z boku, s celým telom v zábere."),
"sl": ("Kamera tega giba še ne ocenjuje. Sledi prikazu; časovnik te vodi.",
       "Stoj z obrazom proti telefonu ali rahlo poševno, z zgornjim delom telesa v kadru.",
       "Postavi telefon na raven tal, s strani, s celim telesom v kadru."),
"sv": ("Kameran bedömer inte den här rörelsen än. Följ demonstrationen; timern guidar dig.",
       "Stå vänd mot telefonen eller lite snett, med överkroppen i bild.",
       "Ställ telefonen i golvhöjd, från sidan, med hela kroppen i bild."),
}

if __name__ == "__main__":
    SRC = json.load(open("tools/i18n/source.json", encoding="utf-8"))
    for p in sorted(glob.glob("app/src/main/assets/i18n/*.json")):
        lang = os.path.basename(p)[:-5]
        head, upper, floor = T[lang]
        t = json.load(open(p, encoding="utf-8"))
        tr = [t[FRAMES[0]], t[FRAMES[1]], upper, floor]
        t[FRAMES[2]], t[FRAMES[3]] = upper, floor
        for f, ft in zip(FRAMES, tr):
            t[HEAD + " " + f] = head + " " + ft
        out = {s: t[s] for s in SRC if s in t and str(t[s]).strip()}
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(lang, len(out), "of", len(SRC))
