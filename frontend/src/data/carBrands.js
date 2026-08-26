/**
 * Марки и модели — для выпадающих списков на лендинге «Авто».
 *
 * Марка не переводится на языки, значения буквально те же везде —
 * backend/app/core/tg_parse.py держит свою копию для распознавания
 * марки в тексте при импорте из Telegram.
 *
 * Модели заведены не под все ~90 марок — под самые ходовые (то, что
 * реально продают в Европе и на Балканах). У остальных марок и у
 * «Другая» вместо выпадающего списка — обычное текстовое поле: полного
 * каталога моделей всех марок мира ни один классифайд руками не ведёт.
 */

export const CAR_BRANDS = [
  'Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Opel', 'Porsche', 'Mini', 'Smart',
  'Renault', 'Peugeot', 'Citroën', 'DS',
  'Fiat', 'Alfa Romeo', 'Lancia', 'Maserati', 'Ferrari', 'Lamborghini',
  'Land Rover', 'Jaguar', 'Bentley', 'Rolls-Royce', 'MG', 'Aston Martin',
  'Škoda', 'Seat', 'Cupra',
  'Volvo', 'Saab',
  'Dacia',
  'Ford', 'Chevrolet', 'Jeep', 'Chrysler', 'Dodge', 'Cadillac', 'GMC', 'Lincoln', 'Tesla',
  'Toyota', 'Honda', 'Nissan', 'Mazda', 'Mitsubishi', 'Suzuki', 'Subaru', 'Lexus', 'Infiniti', 'Daihatsu', 'Isuzu',
  'Hyundai', 'Kia', 'SsangYong', 'Genesis',
  'Chery', 'Geely', 'Great Wall', 'Haval', 'BYD', 'Omoda', 'Jetour', 'JAC', 'DFSK', 'Zeekr', 'NIO', 'Lynk & Co',
  'Другая',
]

export const CAR_MODELS = {
  Audi: ['A1', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'Q2', 'Q3', 'Q5', 'Q7', 'Q8', 'TT', 'e-tron'],
  BMW: ['1 серии', '2 серии', '3 серии', '4 серии', '5 серии', '6 серии', '7 серии', '8 серии', 'X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'Z4', 'i3', 'i4', 'iX'],
  'Mercedes-Benz': ['A-класс', 'B-класс', 'C-класс', 'E-класс', 'S-класс', 'CLA', 'CLS', 'GLA', 'GLB', 'GLC', 'GLE', 'GLS', 'G-класс', 'Vito', 'Sprinter'],
  Volkswagen: ['Polo', 'Golf', 'Jetta', 'Passat', 'Arteon', 'Tiguan', 'Touareg', 'T-Roc', 'T-Cross', 'Touran', 'Sharan', 'Caddy', 'Transporter', 'ID.3', 'ID.4'],
  Opel: ['Corsa', 'Astra', 'Insignia', 'Mokka', 'Crossland', 'Grandland', 'Zafira', 'Vivaro'],
  Porsche: ['911', 'Cayenne', 'Macan', 'Panamera', 'Taycan', 'Boxster', 'Cayman'],
  Renault: ['Clio', 'Megane', 'Talisman', 'Captur', 'Kadjar', 'Koleos', 'Duster', 'Espace', 'Scenic', 'Trafic', 'Kangoo', 'Laguna', 'Fluence'],
  Peugeot: ['208', '308', '408', '508', '2008', '3008', '5008', 'Partner', 'Expert', 'Traveller'],
  Citroën: ['C3', 'C4', 'C5', 'C4 Picasso', 'C5 Aircross', 'Berlingo', 'Jumpy', 'Grand C4 Space Tourer'],
  Fiat: ['500', 'Panda', 'Tipo', 'Punto', 'Doblo', 'Ducato', '500X', 'Bravo'],
  'Alfa Romeo': ['Giulia', 'Giulietta', 'Stelvio', 'MiTo'],
  'Land Rover': ['Range Rover', 'Range Rover Sport', 'Range Rover Evoque', 'Range Rover Velar', 'Discovery', 'Discovery Sport', 'Defender'],
  Jaguar: ['XE', 'XF', 'XJ', 'F-Pace', 'E-Pace', 'I-Pace', 'F-Type'],
  Škoda: ['Fabia', 'Rapid', 'Octavia', 'Superb', 'Kamiq', 'Karoq', 'Kodiaq', 'Scala', 'Yeti'],
  Seat: ['Ibiza', 'Leon', 'Toledo', 'Arona', 'Ateca', 'Tarraco', 'Alhambra'],
  Volvo: ['S60', 'S90', 'V40', 'V60', 'V90', 'XC40', 'XC60', 'XC90'],
  Dacia: ['Sandero', 'Logan', 'Duster', 'Dokker', 'Lodgy', 'Spring'],
  Ford: ['Fiesta', 'Focus', 'Mondeo', 'Kuga', 'EcoSport', 'Puma', 'Galaxy', 'S-Max', 'Transit', 'Ranger', 'Mustang', 'Explorer'],
  Chevrolet: ['Aveo', 'Cruze', 'Spark', 'Captiva', 'Orlando', 'Camaro', 'Malibu'],
  Jeep: ['Renegade', 'Compass', 'Cherokee', 'Grand Cherokee', 'Wrangler'],
  Toyota: ['Yaris', 'Corolla', 'Camry', 'Avensis', 'Auris', 'C-HR', 'RAV4', 'Land Cruiser', 'Hilux', 'Prius', 'Aygo', 'Highlander'],
  Honda: ['Civic', 'Accord', 'CR-V', 'HR-V', 'Jazz', 'Pilot'],
  Nissan: ['Micra', 'Note', 'Juke', 'Qashqai', 'X-Trail', 'Leaf', 'Navara', 'Pathfinder'],
  Mazda: ['2', '3', '6', 'CX-3', 'CX-5', 'CX-30', 'MX-5'],
  Mitsubishi: ['Colt', 'Lancer', 'ASX', 'Outlander', 'Eclipse Cross', 'Pajero', 'L200'],
  Suzuki: ['Swift', 'Baleno', 'Vitara', 'SX4', 'S-Cross', 'Jimny'],
  Subaru: ['Impreza', 'Legacy', 'Forester', 'Outback', 'XV'],
  Lexus: ['IS', 'ES', 'GS', 'LS', 'NX', 'RX', 'UX', 'CT'],
  Hyundai: ['i10', 'i20', 'i30', 'Elantra', 'Accent', 'Tucson', 'Santa Fe', 'Kona', 'ix35', 'Solaris'],
  Kia: ['Picanto', 'Rio', 'Ceed', 'Cerato', 'Optima', 'Sportage', 'Sorento', 'Niro', 'Soul', 'Stonic'],
  SsangYong: ['Korando', 'Rexton', 'Tivoli', 'Actyon'],
  Chery: ['Tiggo 4', 'Tiggo 7', 'Tiggo 8', 'Arrizo 5'],
  Geely: ['Coolray', 'Atlas', 'Emgrand', 'Tugella'],
  'Great Wall': ['Poer', 'Wingle'],
  Haval: ['Jolion', 'H6', 'Dargo'],
  BYD: ['Atto 3', 'Han', 'Tang', 'Seal', 'Dolphin'],
}

export const CAR_MODEL_OTHER = 'Другая'
