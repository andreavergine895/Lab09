from database.regione_DAO import RegioneDAO
from database.tour_DAO import TourDAO
from database.attrazione_DAO import AttrazioneDAO



class Model:
    def __init__(self):
        self.tour_map = {} # Mappa ID tour -> oggetti Tour
        self.attrazioni_map = {} # Mappa ID attrazione -> oggetti Attrazione

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # TODO: Aggiungere eventuali altri attributi
        # Parametri ricorsione
        self._max_giorni = None
        self._max_budget = None
        self._tour_regione = []

        # Caricamento
        self.load_tour()
        self.load_attrazioni()
        self.load_relazioni()

    @staticmethod
    def load_regioni():
        """ Restituisce tutte le regioni disponibili """
        return RegioneDAO.get_regioni()

    def load_tour(self):
        """ Carica tutti i tour in un dizionario [id, Tour]"""
        self.tour_map = TourDAO.get_tour()

    def load_attrazioni(self):
        """ Carica tutte le attrazioni in un dizionario [id, Attrazione]"""
        self.attrazioni_map = AttrazioneDAO.get_attrazioni()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra tour e attrazioni e salvarle nelle strutture dati
            Collega tour <-> attrazioni.
            --> Ogni Tour ha un set di Attrazione.
            --> Ogni Attrazione ha un set di Tour.
        """
        relazioni = TourDAO.get_tour_attrazioni()
        for row in relazioni:
            id_tour= row["id_tour"]
            id_attrazione= row["id_attrazione"]

            tour = self.tour_map.get(id_tour)
            attrazione = self.attrazioni_map.get(id_attrazione)

            if tour is None or attrazione is None:
                continue
                # Aggiungo la relazione
            tour.attrazioni.add(attrazione)
            attrazione.tour.add(tour)
    def genera_pacchetto(self, id_regione: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto turistico ottimale per una regione rispettando i vincoli di durata, budget e attrazioni uniche.
        :param id_regione: id della regione
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Tour)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il valore culturale del pacchetto)
        """
        # Reset delle soluzioni ottimali trovate nelle precedenti chiamate
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        # Imposto i vincoli: se l'utente non specifica, uso infinito (nessun vincolo)
        for tour in self.tour_map.values():
            if tour.id_regione == id_regione:
                self._tour_regione.append(tour)

        # Imposto i vincoli: se l'utente non specifica, uso infinito (nessun vincolo)
        self._max_giorni = max_giorni if max_giorni is not None else float("inf")
        self._max_budget = max_budget if max_budget is not None else float("inf")

        # Avvio la ricorsione: partendo dall'indice 0, pacchetto vuoto e valori a 0
        self._ricorsione(0,[],0, 0,0,set())

        # Ritorno il pacchetto ottimo trovato, il costo associato e il valore culturale totale
        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index, pacchetto_parziale, durata_corrente,
                    costo_corrente, valore_corrente, attrazioni_usate):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il valore culturale"""

        # --- A: aggiornamento della soluzione migliore trovata finora ---
        # Se il valore corrente è migliore del migliore precedente, aggiorno soluzione ottima
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente  # memorizzo nuovo valore massimo
            self._pacchetto_ottimo = pacchetto_parziale.copy()  # memorizzo copia del pacchetto corrente
            self._costo = costo_corrente  # memorizzo costo corrente

        # Scorro i tour rimanenti a partire dall'indice start_index
        # (in questo modo evito combinazioni duplicate permutate e garantisco tour diversi)
        for i in range(start_index, len(self._tour_regione)):
            tour = self._tour_regione[i]

            # --- C: verifico i vincoli prima di procedere con la ricorsione ---

            # Vincolo durata: se aggiungendo il tour sforo i giorni massimi, salto il tour
            if durata_corrente + tour.durata_giorni > self._max_giorni:
                continue

            # Vincolo budget: se aggiungendo il tour sforo il budget massimo, salto il tour
            if costo_corrente + tour.costo > self._max_budget:
                continue

            # Vincolo attrazioni uniche: se il tour ha una qualsiasi attrazione già usata, salto
            # isdisjoint restituisce True se i due set non hanno elementi in comune
            if not tour.attrazioni.isdisjoint(attrazioni_usate):
                continue

            # --- D: aggiorno i parametri parziali (scelta del tour corrente) ---

            pacchetto_parziale.append(tour)  # aggiungo il tour al pacchetto parziale

            nuove_attr = tour.attrazioni  # le attrazioni del tour che sto per aggiungere
            old_attr = attrazioni_usate.copy()  # salvo lo stato delle attrazioni prima di modificarlo
            attrazioni_usate.update(nuove_attr)  # unisco le nuove attrazioni a quelle già usate

            # sommo il valore culturale delle attrazioni del tour al valore corrente
            nuovo_valore = valore_corrente + sum(a.valore_culturale for a in tour.attrazioni)
            nuova_durata = durata_corrente + tour.durata_giorni
            nuovo_costo = costo_corrente + tour.costo

            # --- E: ricorsione sul sottoproblema che considera solo i tour successivi (i+1) ---
            # passiamo i nuovi stati: i+1 come start_index evita ripetizioni / permutazioni
            self._ricorsione(
                i + 1,
                pacchetto_parziale,
                nuova_durata,
                nuovo_costo,
                nuovo_valore,
                attrazioni_usate
            )

            # --- F: backtracking → ripristino lo stato prima di provare il prossimo tour ---
            pacchetto_parziale.pop()  # rimuovo l'ultimo tour aggiunto
            attrazioni_usate.clear()  # ripristino il set delle attrazioni a old_attr
            attrazioni_usate.update(old_attr)
