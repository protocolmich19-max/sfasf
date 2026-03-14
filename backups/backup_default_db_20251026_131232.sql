-- Backup generated at 20251026_131232 UTC
-- Database: `default_db`

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;
SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';
SET time_zone = '+00:00';


--
-- Table structure for `balance_transafers`
--

DROP TABLE IF EXISTS `balance_transafers`;
CREATE TABLE `balance_transafers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `to_user_id` int DEFAULT NULL,
  `from_user_id` int DEFAULT NULL,
  `money` int DEFAULT NULL,
  `created_at` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `balance_transafers`
--
INSERT INTO `balance_transafers` VALUES (1,11,10,20,1754475378);
INSERT INTO `balance_transafers` VALUES (2,11,85,0,1754728196);
INSERT INTO `balance_transafers` VALUES (3,28,11,13,1755530284);
INSERT INTO `balance_transafers` VALUES (4,108,38,3333,1756649121);
INSERT INTO `balance_transafers` VALUES (5,11,38,5000,1757950912);


--
-- Table structure for `bookings`
--

DROP TABLE IF EXISTS `bookings`;
CREATE TABLE `bookings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `event_id` int NOT NULL,
  `city_id` int NOT NULL,
  `name` varchar(200) NOT NULL,
  `persons` int NOT NULL,
  `status` enum('pending','confirmed','cancelled') NOT NULL,
  `payment_status` enum('none','paid_mock') NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_bookings_user_id` (`user_id`),
  KEY `ix_bookings_event_id` (`event_id`),
  KEY `ix_bookings_city_id` (`city_id`),
  KEY `ix_bookings_city_id_created_at` (`city_id`,`created_at`),
  CONSTRAINT `fk_bookings_city_id_cities` FOREIGN KEY (`city_id`) REFERENCES `cities` (`id`),
  CONSTRAINT `fk_bookings_event_id_events` FOREIGN KEY (`event_id`) REFERENCES `events` (`id`),
  CONSTRAINT `fk_bookings_user_id_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `bookings`
--


--
-- Table structure for `cities`
--

DROP TABLE IF EXISTS `cities`;
CREATE TABLE `cities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `text` varchar(255) DEFAULT NULL,
  `agent_account` varchar(255) DEFAULT NULL,
  `channel_link` varchar(255) DEFAULT NULL,
  `created_at` int DEFAULT NULL,
  `slug` varchar(100) NOT NULL DEFAULT 'default',
  `channel_url` varchar(255) DEFAULT NULL,
  `representative_contact` varchar(255) DEFAULT NULL,
  `creator_chat_id` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `main_message` text,
  `main_media` json DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `cities`
--
INSERT INTO `cities` VALUES (1,'Москва','1','@','',0,'default',NULL,NULL,NULL,1,'тест 1',NULL);
INSERT INTO `cities` VALUES (2,'Калининград','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (3,'Санкт-Петербург','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (4,'Уфа','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (5,'Иркутск','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (6,'Петропавловск-Камчатский','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (7,'Краснодар','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (8,'Сочи','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (9,'Анапа','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (10,'Симферополь','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (11,'Адлер','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (12,'Красная поляна','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (13,'Казань','','@','',0,'default',NULL,NULL,NULL,1,NULL,NULL);
INSERT INTO `cities` VALUES (14,'Ростов','','@',' ',0,'default',NULL,NULL,NULL,1,NULL,NULL);


--
-- Table structure for `city_bookings`
--

DROP TABLE IF EXISTS `city_bookings`;
CREATE TABLE `city_bookings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `event_id` int NOT NULL,
  `city_id` int NOT NULL,
  `name` varchar(200) NOT NULL,
  `persons` int NOT NULL,
  `status` enum('pending','confirmed','cancelled') NOT NULL,
  `payment_status` enum('none','paid_mock') NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_bookings_city_id_created_at` (`city_id`,`created_at`),
  KEY `ix_city_bookings_user_id` (`user_id`),
  KEY `ix_city_bookings_event_id` (`event_id`),
  KEY `ix_city_bookings_city_id` (`city_id`),
  CONSTRAINT `fk_city_bookings_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`),
  CONSTRAINT `fk_city_bookings_event_id_city_events` FOREIGN KEY (`event_id`) REFERENCES `city_events` (`id`),
  CONSTRAINT `fk_city_bookings_user_id_city_users` FOREIGN KEY (`user_id`) REFERENCES `city_users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_bookings`
--
INSERT INTO `city_bookings` VALUES (15,3,1,1,'hamstervadim',1,'confirmed','none','2025-10-12 09:19:27');
INSERT INTO `city_bookings` VALUES (16,5,1,1,'hamstervadim',1,'confirmed','none','2025-10-16 14:22:19');
INSERT INTO `city_bookings` VALUES (17,6,1,1,'Ksusha_Dusha',1,'confirmed','none','2025-10-16 14:22:28');


--
-- Table structure for `city_cities`
--

DROP TABLE IF EXISTS `city_cities`;
CREATE TABLE `city_cities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `slug` varchar(100) NOT NULL,
  `channel_url` varchar(255) DEFAULT NULL,
  `representative_contact` varchar(255) DEFAULT NULL,
  `creator_chat_id` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `main_message` text,
  `main_media` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_city_cities_name` (`name`),
  KEY `ix_city_cities_slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_cities`
--
INSERT INTO `city_cities` VALUES (1,'Москва','moscow',NULL,NULL,1,1,'Привет!Рада Тебе!\r\nНа связи Ксюша Душанова. \r\nГенеральный продюсер и соавтор проекта \"За Любовь\"\r\nЗдесь Ты узнаешь расписание всех моих игр и мероприятий \"За Любовь\", познакомишься с аккредитованными мной партнерами. Найдешь самые интересные мероприятия оффлайн и онлайн с моим участием. Так же у Тебя теперь есть возможность узнавать самые горячие новости и выгодные условия одним из первых. \r\nРасполагайся по удобней...\r\nПолетели!','{\"photo_url\": \"/media/events/48c22ceee47b41e5a37a88cb998faad2.jpg\"}');


--
-- Table structure for `city_events`
--

DROP TABLE IF EXISTS `city_events`;
CREATE TABLE `city_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `city_id` int NOT NULL,
  `description` varchar(2000) DEFAULT NULL,
  `media` json DEFAULT NULL,
  `venue_address` varchar(255) DEFAULT NULL,
  `starts_at` datetime DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_events_starts_at` (`starts_at`),
  KEY `ix_city_events_city_id_starts_at` (`city_id`,`starts_at`),
  KEY `ix_city_events_city_id` (`city_id`),
  CONSTRAINT `fk_city_events_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_events`
--
INSERT INTO `city_events` VALUES (1,1,'тест 1','null',NULL,'2025-10-25 02:45:00',20,1);


--
-- Table structure for `city_organizers`
--

DROP TABLE IF EXISTS `city_organizers`;
CREATE TABLE `city_organizers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `city_id` int NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_city_organizers_username` (`username`),
  KEY `ix_city_organizers_username` (`username`),
  KEY `ix_city_organizers_city_id` (`city_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_organizers`
--
INSERT INTO `city_organizers` VALUES (1,'Ksusha_Dusha','AsstpZdC',1,1);


--
-- Table structure for `city_other_bookings`
--

DROP TABLE IF EXISTS `city_other_bookings`;
CREATE TABLE `city_other_bookings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `other_event_id` int NOT NULL,
  `city_id` int NOT NULL,
  `name` varchar(200) NOT NULL,
  `persons` int NOT NULL,
  `status` enum('pending','confirmed','cancelled') NOT NULL,
  `payment_status` enum('none','paid_mock') NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_city_other_bookings_other_event_id_city_other_events` (`other_event_id`),
  KEY `fk_city_other_bookings_city_id_city_cities` (`city_id`),
  KEY `ix_city_other_bookings_user_id` (`user_id`),
  CONSTRAINT `fk_city_other_bookings_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`),
  CONSTRAINT `fk_city_other_bookings_other_event_id_city_other_events` FOREIGN KEY (`other_event_id`) REFERENCES `city_other_events` (`id`),
  CONSTRAINT `fk_city_other_bookings_user_id_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_other_bookings`
--


--
-- Table structure for `city_other_events`
--

DROP TABLE IF EXISTS `city_other_events`;
CREATE TABLE `city_other_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `city_id` int NOT NULL,
  `description` varchar(2000) DEFAULT NULL,
  `media` json DEFAULT NULL,
  `venue_address` varchar(255) DEFAULT NULL,
  `starts_at` datetime DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_other_events_city_id` (`city_id`),
  CONSTRAINT `fk_city_other_events_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_other_events`
--


--
-- Table structure for `city_pay_metadatas`
--

DROP TABLE IF EXISTS `city_pay_metadatas`;
CREATE TABLE `city_pay_metadatas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `price` int NOT NULL,
  `product` varchar(255) NOT NULL,
  `procent_balance` int NOT NULL,
  `inner_balance` int NOT NULL,
  `has_payed` int NOT NULL,
  `created_at` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_pay_metadatas_user_id` (`user_id`),
  KEY `ix_city_pay_metadatas_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_pay_metadatas`
--
INSERT INTO `city_pay_metadatas` VALUES (1,346,1000,'subscribe-1',0,0,1,1758974009);
INSERT INTO `city_pay_metadatas` VALUES (2,347,5000,'package',0,0,1,1758974009);
INSERT INTO `city_pay_metadatas` VALUES (3,346,2000,'game',0,0,1,1758887609);


--
-- Table structure for `city_products`
--

DROP TABLE IF EXISTS `city_products`;
CREATE TABLE `city_products` (
  `id` int NOT NULL AUTO_INCREMENT,
  `city_id` int DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `description` text,
  `price_minor` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `media` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_products_city_id` (`city_id`),
  CONSTRAINT `fk_city_products_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_products`
--
INSERT INTO `city_products` VALUES (1,1,'тест 2','тест 1',NULL,1,'null');


--
-- Table structure for `city_referrals`
--

DROP TABLE IF EXISTS `city_referrals`;
CREATE TABLE `city_referrals` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `city_id` int NOT NULL,
  `code` varchar(100) NOT NULL,
  `source` varchar(50) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_city_referrals_code` (`code`),
  KEY `ix_city_referrals_city_id` (`city_id`),
  KEY `ix_city_referrals_user_id` (`user_id`),
  CONSTRAINT `fk_city_referrals_city_id_city_cities` FOREIGN KEY (`city_id`) REFERENCES `city_cities` (`id`),
  CONSTRAINT `fk_city_referrals_user_id_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_referrals`
--


--
-- Table structure for `city_users`
--

DROP TABLE IF EXISTS `city_users`;
CREATE TABLE `city_users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tg_id` bigint NOT NULL,
  `username` varchar(255) DEFAULT NULL,
  `full_name` varchar(255) DEFAULT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `balance` float NOT NULL DEFAULT '0',
  `inner_balance` float NOT NULL DEFAULT '0',
  `has_ended` tinyint(1) NOT NULL DEFAULT '0',
  `ref` bigint DEFAULT NULL,
  `ref_level` int NOT NULL DEFAULT '0',
  `created_at` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_tg_id` (`tg_id`),
  KEY `ix_city_users_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `city_users`
--
INSERT INTO `city_users` VALUES (7,6742056004,'hamstervadim',NULL,NULL,'1',0.0e0,0.0e0,0,NULL,0,1759409828);
INSERT INTO `city_users` VALUES (8,241954492,'Ksusha_Dusha',NULL,NULL,'1',0.0e0,0.0e0,0,NULL,0,1759409828);


--
-- Table structure for `events`
--

DROP TABLE IF EXISTS `events`;
CREATE TABLE `events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `city_id` int NOT NULL,
  `description` varchar(2000) DEFAULT NULL,
  `media` json DEFAULT NULL,
  `venue_address` varchar(255) DEFAULT NULL,
  `starts_at` datetime DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_events_starts_at` (`starts_at`),
  KEY `ix_events_city_id` (`city_id`),
  KEY `ix_events_city_id_starts_at` (`city_id`,`starts_at`),
  CONSTRAINT `fk_events_city_id_cities` FOREIGN KEY (`city_id`) REFERENCES `cities` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `events`
--


--
-- Table structure for `organizers`
--

DROP TABLE IF EXISTS `organizers`;
CREATE TABLE `organizers` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `city_id` int NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_organizers_username` (`username`),
  KEY `ix_organizers_city_id` (`city_id`),
  KEY `ix_organizers_username` (`username`),
  CONSTRAINT `fk_organizers_city_id_cities` FOREIGN KEY (`city_id`) REFERENCES `cities` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `organizers`
--


--
-- Table structure for `other_bookings`
--

DROP TABLE IF EXISTS `other_bookings`;
CREATE TABLE `other_bookings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `other_event_id` int NOT NULL,
  `city_id` int NOT NULL,
  `name` varchar(200) NOT NULL,
  `persons` int NOT NULL,
  `status` enum('pending','confirmed','cancelled') NOT NULL,
  `payment_status` enum('none','paid_mock') NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_other_bookings_other_event_id_other_events` (`other_event_id`),
  KEY `fk_other_bookings_city_id_cities` (`city_id`),
  KEY `ix_other_bookings_user_id` (`user_id`),
  CONSTRAINT `fk_other_bookings_city_id_cities` FOREIGN KEY (`city_id`) REFERENCES `cities` (`id`),
  CONSTRAINT `fk_other_bookings_other_event_id_other_events` FOREIGN KEY (`other_event_id`) REFERENCES `other_events` (`id`),
  CONSTRAINT `fk_other_bookings_user_id_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `other_bookings`
--


--
-- Table structure for `other_events`
--

DROP TABLE IF EXISTS `other_events`;
CREATE TABLE `other_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `city_id` int NOT NULL,
  `description` varchar(2000) DEFAULT NULL,
  `media` json DEFAULT NULL,
  `venue_address` varchar(255) DEFAULT NULL,
  `starts_at` datetime DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_other_events_city_id` (`city_id`),
  CONSTRAINT `fk_other_events_city_id_cities` FOREIGN KEY (`city_id`) REFERENCES `cities` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `other_events`
--


--
-- Table structure for `pay_metadatas`
--

DROP TABLE IF EXISTS `pay_metadatas`;
CREATE TABLE `pay_metadatas` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `price` int NOT NULL,
  `product` varchar(255) NOT NULL,
  `procent_balance` int NOT NULL,
  `inner_balance` int NOT NULL,
  `has_payed` int NOT NULL,
  `created_at` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_pay_metadatas_user_id` (`user_id`),
  KEY `ix_pay_metadatas_created_at` (`created_at`),
  CONSTRAINT `fk_pay_metadatas_user_id_users` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=90 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `pay_metadatas`
--
INSERT INTO `pay_metadatas` VALUES (1,756,199,'poster',10,0,1,1759409828);
INSERT INTO `pay_metadatas` VALUES (2,768,5000,'package',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (3,768,5000,'package',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (4,768,55555,'game',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (5,768,55555,'game',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (6,768,79999,'clubtraining',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (7,768,333333,'citymanager',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (8,768,5000,'package',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (9,773,199,'poster',10,0,1,1760200744);
INSERT INTO `pay_metadatas` VALUES (10,739,199,'poster',10,0,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (11,773,199,'poster',10,0,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (12,773,199,'poster',10,0,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (13,773,199,'poster',10,0,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (14,773,199,'poster',10,0,1,1760200744);
INSERT INTO `pay_metadatas` VALUES (15,804,99999,'allpackage',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (16,807,333333,'citymanager',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (17,789,79999,'clubtraining',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (18,807,99999,'allpackage',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (19,810,5000,'package',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (20,810,79999,'clubtraining',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (21,810,333333,'citymanager',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (22,813,333333,'citymanager',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (23,813,99999,'allpackage',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (24,813,5000,'package',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (25,823,79999,'clubtraining',25,25,0,1760200744);
INSERT INTO `pay_metadatas` VALUES (26,833,199,'poster',10,0,1,1760200744);
INSERT INTO `pay_metadatas` VALUES (27,739,5000,'package',25,25,0,1760952125);
INSERT INTO `pay_metadatas` VALUES (28,735,333,'subscribe-1',50,0,0,1761053914);
INSERT INTO `pay_metadatas` VALUES (29,735,333,'subscribe-1',50,0,0,1761063659);
INSERT INTO `pay_metadatas` VALUES (30,733,3333,'subscribe-12',50,0,0,1761063662);
INSERT INTO `pay_metadatas` VALUES (31,733,3333,'subscribe-12',0,0,1,1761063662);
INSERT INTO `pay_metadatas` VALUES (32,813,79999,'clubtraining',25,25,0,1761171933);
INSERT INTO `pay_metadatas` VALUES (33,813,333333,'citymanager',25,25,0,1761172200);
INSERT INTO `pay_metadatas` VALUES (34,813,5000,'package',25,25,0,1761172241);
INSERT INTO `pay_metadatas` VALUES (35,813,99999,'allpackage',25,25,0,1761172250);
INSERT INTO `pay_metadatas` VALUES (36,735,3333,'subscribe-12',0,0,1,1761063662);
INSERT INTO `pay_metadatas` VALUES (37,740,99999,'allpackage',25,25,0,1761233993);
INSERT INTO `pay_metadatas` VALUES (38,740,55555,'game',25,25,0,1761234021);
INSERT INTO `pay_metadatas` VALUES (39,810,5000,'package',25,25,0,1761375925);
INSERT INTO `pay_metadatas` VALUES (40,810,99999,'allpackage',25,25,0,1761375928);
INSERT INTO `pay_metadatas` VALUES (41,860,5000,'package',25,25,0,1761411255);
INSERT INTO `pay_metadatas` VALUES (42,860,99999,'allpackage',25,25,0,1761411262);
INSERT INTO `pay_metadatas` VALUES (43,860,5000,'package',25,25,0,1761411394);
INSERT INTO `pay_metadatas` VALUES (44,860,55555,'game',25,25,0,1761411467);
INSERT INTO `pay_metadatas` VALUES (63,739,1,'subscribe-12',0,0,1,1761417807);
INSERT INTO `pay_metadatas` VALUES (64,740,1,'subscribe-12',0,0,1,1761417807);
INSERT INTO `pay_metadatas` VALUES (65,731,1,'subscribe-12',0,0,1,1761417807);
INSERT INTO `pay_metadatas` VALUES (66,766,1,'subscribe-12',0,0,1,1761417807);


--
-- Table structure for `poster_files`
--

DROP TABLE IF EXISTS `poster_files`;
CREATE TABLE `poster_files` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key` varchar(256) NOT NULL,
  `mime_type` varchar(128) NOT NULL,
  `data` blob NOT NULL,
  `created_at` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_poster_files_key` (`key`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb3;

--
-- Dumping data for table `poster_files`
--
