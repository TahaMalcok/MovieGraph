import json
import os
from neo4j import GraphDatabase, basic_auth

class MovieGraphApp:
    def __init__(self, uri, user, password):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=basic_auth(user, password))
            self.driver.verify_connectivity()
            print("Neo4j bağlantısı vardır.")
        except Exception as e:
            print(f"Neo4j bağlantısı yoktur. Hata: {e}")

    def kapa(self):
        if self.driver:
            self.driver.close()
            print("Bağlantı kesildi.")

    def film_arama(self, kelime):
        if not kelime.strip():
            print("Boş giriş yapılmıştır.")
            return

        query = "MATCH (m:Movie) where m.title CONTAINS $kelime RETURN m.title AS title, m.released AS released ORDER BY m.released ASC"

        with self.driver.session() as session:
            result = session.run(query, kelime=kelime)
            movies = [record for record in result]

        if not movies:
            print(f"{kelime} kelimesi ile eşleşen bir film bulunamadı.")
            return

        print(f"{kelime} için sonuçlar:")
        for index, record in enumerate(movies, 1):
            print(f"{index}. {record['title']} ({record['released']})")

        return movies

    def film_detaylandırma(self, title):
        query = """
        MATCH (m:Movie {title: $title}) OPTIONAL MATCH (d:Person)-[:DIRECTED]->(m) OPTIONAL MATCH (a:Person)-[:ACTED_IN]->(m)
        RETURN m.title AS title, m.released AS released, m.tagline AS tagline, collect(DISTINCT d.name) AS directors, collect(DISTINCT a.name)[0..5] AS actors
        """

        with self.driver.session() as session:
            result = session.run(query, title=title)
            record = result.single()
            if record:
                return{
                    "title": record['title'],
                    "released": record['released'],
                    "tagline": record['tagline'],
                    "directors": record['directors'],
                    "actors": record['actors']
                }
            else:
                return None

    def grafik(self, title):
        query = """MATCH (m:Movie {title: $title}) OPTIONAL MATCH (d:Person)-[r]-(m) RETURN m.title AS movie, d.name AS person, type(r) AS relationship """

        links = []
        nodes = []
        added_ids = set()

        with self.driver.session() as session:
            result = session.run(query, title=title)
            if title not in added_ids:
                nodes.append({"id": title, "label": "Movie"})
                added_ids.add(title)
            for record in result:
                person = record['person']
                rel_type = record['relationship']
                if person and person not in added_ids:
                    nodes.append({"id": person, "label": "Person"})
                    added_ids.add(person)

                if person:
                    links.append({"source": person, "target": title, "type": rel_type})

        output_data = {"nodes": nodes, "links": links}
        if not os.path.exists("exports"):
            os.makedirs("exports")
        file_path = "exports/graph.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"{title} isimli film için ağ verisi {file_path} isimli dosyaya kaydedildi.")
        except Exception as e:
            print(f"Dosya yazma hatası({e})")

def main():
    app = MovieGraphApp("neo4j://127.0.0.1:7687", "neo4j", "taha2005")

    seçilen_film = None
    filmler = []
    print("Sisteme Hoş Geldiniz")
    while True:
        print("Film Arama Arayüzü")
        print("1. Film Ara")
        print("2. Film Detayı Göster")
        print("3. Film Ağı Oluştur")
        print("4. Çıkış")
        seçim = input("Seçiminizi yapınız(1-4):")

        if seçim == "1":
            kelime = input("Aramak istediğiniz kelimeyi giriniz:")
            filmler = app.film_arama(kelime)

        elif seçim == "2":
            if not filmler:
                print("Lütfen önce film arayınız ve listeden bir film seçiniz.")
                continue
            try:
                numara = int(input(f"Detayını görmek istediğiniz filmin numarasını giriniz(1-{len(filmler)}):"))
                if 1 <= numara <= len(filmler):
                    film_data = filmler[numara-1]
                    seçilen_film = film_data['title']
                    detaylar = app.film_detaylandırma(seçilen_film)
                    if detaylar:
                        print(f"ADI: {detaylar['title']}")
                        print(f"YILI: {detaylar['released']}")
                        if detaylar["tagline"]:
                            print(f"SLOGANI: {detaylar['tagline']}")
                        print(f"YÖNETMEN: {', '.join(detaylar['directors'])}")
                        print(f"OYUNCULAR: {', '.join(detaylar['actors'])}")
                    else:
                        print("Filme ait detay bulunamadı.")
                else:
                    print("Geçersiz bir numara girdiniz. Lütfen geçerli bir değer giriniz.")
            except ValueError:
                print("Lütfen geçerli bir sayı girin!")
        elif seçim == "3":
            if seçilen_film:
                app.grafik(seçilen_film)
            else:
                print("Öncelikle bir film aramalı sonrasında bu filmin detaylarına bakmalısınız.")


        elif seçim == "4":
            app.kapa()
            print("Sistemnden çıkış yapılıyor.")
            break

        else:
            print("Geçersiz değer girdiniz.")

main()