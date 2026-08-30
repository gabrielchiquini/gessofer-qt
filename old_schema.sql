BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "configs" (
	"id"	INTEGER,
	"cloudPath"	TEXT,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "contacts" (
	"id"	INTEGER,
	"name"	TEXT,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	"fkPhoneType"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkPhoneType") REFERENCES "phoneTypes"("id") ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "expenses" (
	"id"	INTEGER,
	"name"	TEXT,
	"value"	REAL,
	"month"	REAL,
	"year"	REAL,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "nota" (
	"id"	INTEGER,
	"data"	DATETIME,
	"fornecedor"	TEXT,
	"chaveNFE"	TEXT,
	"frete"	REAL,
	"descarga"	REAL,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "phoneTypes" (
	"id"	INTEGER,
	"text"	TEXT,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "phones" (
	"id"	INTEGER,
	"phone"	TEXT,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	"fkContact"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkContact") REFERENCES "contacts"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS "produtos" (
	"id"	INTEGER,
	"nome"	TEXT,
	"quantidade"	REAL,
	"precoUnitario"	REAL,
	"precoTotal"	REAL,
	"createdAt"	DATETIME NOT NULL,
	"updatedAt"	DATETIME NOT NULL,
	"fkNota"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("fkNota") REFERENCES "nota"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE VIEW contactView AS
                    SELECT c.id AS contactId, c.name, pt.text AS type, pt.id AS typeId, lower(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace( name, 'á','a'), 'ã','a'), 'â','a'), 'é','e'), 'ê','e'), 'í','i'), 'ó','o') ,'õ','o') ,'ô','o'),'ú','u'), 'ç','c'),'Á','A'), 'Ã','A'), 'Â','A'), 'É','E'), 'Ê','E'), 'Í','I'), 'Ó','O') ,'Õ','O') ,'Ô','O'),'Ú','U'), 'Ç','C')) as nameNormal
                    FROM contacts c JOIN phoneTypes pt
                    ON c.fkPhoneType = pt.id;
CREATE VIEW viewNota AS SELECT `data`, fornecedor, lower(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace( fornecedor, 'á','a'), 'ã','a'), 'â','a'), 'é','e'), 'ê','e'), 'í','i'), 'ó','o') ,'õ','o') ,'ô','o'),'ú','u'), 'ç','c'),'Á','A'), 'Ã','A'), 'Â','A'), 'É','E'), 'Ê','E'), 'Í','I'), 'Ó','O') ,'Õ','O') ,'Ô','O'),'Ú','U'), 'Ç','C')) as fornecedorNormal, nome AS produto, lower(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace( replace(replace(replace( nome, 'á','a'), 'ã','a'), 'â','a'), 'é','e'), 'ê','e'), 'í','i'), 'ó','o') ,'õ','o') ,'ô','o'),'ú','u'), 'ç','c'),'Á','A'), 'Ã','A'), 'Â','A'), 'É','E'), 'Ê','E'), 'Í','I'), 'Ó','O') ,'Õ','O') ,'Ô','O'),'Ú','U'), 'Ç','C')) as produtoNormal, quantidade, precoUnitario, precoTotal
    FROM nota n JOIN produtos p ON n.id = p.fkNota;
COMMIT;
