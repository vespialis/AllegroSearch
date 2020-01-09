from pyAllegro.api import AllegroRestApi
from decimal import Decimal


def check_seller(seller_id, min_rating):
    status_code_rating, json_data_rating = RestApi.resource_get(
        resource_name='/users/{userId}/ratings-summary'.format(
            **{'userId': seller_id}),
        params={}
    )
    if 'averageRates' not in json_data_rating:
        print('Sprzedawca nie ma wystarczającej ilości ocen -> usuwam przedmioty z listy')
        return False
    else:
        rating = Decimal(json_data_rating['averageRates']['deliveryCost']) + Decimal(json_data_rating[
                        'averageRates']['service']) + Decimal(json_data_rating['averageRates']['description'])
        rating = rating / 3
    if rating > min_rating:
        return True
    else:
        return False


def insert_rating():
    try:
        val = float(input("Wpisz minimalną ocenę sprzedawcy (0-5):\n"))
        if val < 0 or val > 5:
            print("Podano nieprawidłową wartość")
            return insert_rating()
        else:
            return val
    except ValueError:
        print("Podano nieprawidłową wartość")
        return insert_rating()


def insert_count():
    try:
        val = int(input("Wpisz ilość produktów (maksymalnie 5):\n"))
        if val < 0 or val > 5:
            print("Podano nieprawidłową wartość")
            return insert_count()
        else:
            return val
    except ValueError:
        print("Podano nieprawidłową wartość")
        return insert_count()


def check_pricing(is_price_min, products_pricing_t2):
    try:
        if is_price_min:
            price = int(input('Podaj cenę minimalną:'))
        else:
            price = int(input('Podaj cenę maksymalną:'))
        if price < 0:
            print('Podano liczbę mniejszą od 0.')
            return check_pricing(is_price_min, products_pricing_t2)
        if not is_price_min:
            if price < products_pricing_t2[-1]:
                print('Cena maksymalna jest mniejsza od minimalnej!')
                return check_pricing(is_price_min, products_pricing_t2)
        return price
    except ValueError:
        print('Podano nieprawidłową wartość.')
        return check_pricing(is_price_min, products_pricing_t2)


def insert_products(products_pricing_t, products_t):
    products_t.append(input('Podaj nazwę przedmiotu:'))
    products_pricing_t.append(check_pricing(True, products_pricing_t))
    products_pricing_t.append(check_pricing(False, products_pricing_t))


RestApi = AllegroRestApi()
RestApi.credentials_set(
    appName='xxx',
    clientId='xxx',
    clientSecred='xxx',
    redirectUrl='http://localhost:8000'
)

print("Startuję aplikacje...\nAkceptuj wymaganą przez Allegro autoryzację")
RestApi.get_token()
min_rating = insert_rating()
product_count = insert_count()
products = []
products_pricing = []
status_code_results = []
json_data = []
results = []
for j in range(product_count):
    insert_products(products_pricing, products)

for i in range(len(products)):
    status_code_results_temp, json_data_results_temp = RestApi.resource_get(
        resource_name='/offers/listing',
        params={'phrase': products[i],
                'limit': 100,
                'sort': '+withDeliveryPrice',
                'price.from': products_pricing[2 * i],
                'price.to': products_pricing[2 * i + 1],
                'offerTypeBuyNow:': 1}
    )
    if (len(json_data_results_temp['items']['promoted']) + len(json_data_results_temp['items']['regular'])) == 0:
        print('Nie znaleziono żadnych przedmiotów dla wyszukiwania: ' + products[i])
        print('Uruchom program od nowa wpisując inną nazwę przedmiotu lub ustawiając inną minimalną ocenę.')
        raise SystemExit(0)
    status_code_results.append(status_code_results_temp)
    json_data.append(json_data_results_temp)
    results.append(json_data_results_temp['items']['promoted'] + json_data_results_temp['items']['regular'])
    if len(json_data_results_temp['items']['promoted']) > 0 and len(json_data_results_temp['items']['regular']) > 0:
        results[-1] = sorted(results[-1], key=lambda y: (
                Decimal(y['sellingMode']['price']['amount']) + Decimal(y['delivery']['lowestPrice']['amount'])))

# these complicated loops are creating list of lists of items from each phrase that has the same seller ;)
if len(results) > 1:
    duplicate_seller_items = {}
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            do_break = False
            for k in range(len(results[i])):
                if do_break:
                    break
                for l in range(len(results[j])):
                    if results[i][k]['seller']['id'] == results[j][l]['seller']['id']:
                        if results[i][k]['seller']['id'] in duplicate_seller_items.keys():
                            is_added = False
                            for x in range(len(duplicate_seller_items[results[i][k]['seller']['id']])):
                                if duplicate_seller_items[results[i][k]['seller']['id']][x]['id'] == results[i][k][
                                                                         'id']:
                                    is_added = True
                                    break
                            if not is_added:
                                results[i][k].update({'phrase': products[i]})
                                duplicate_seller_items[results[i][k]['seller']['id']].append(results[i][k])
                            is_added = False
                            for x in range(len(duplicate_seller_items[results[i][k]['seller']['id']])):
                                if duplicate_seller_items[results[i][k]['seller']['id']][x]['id'] == results[j][l][
                                                                         'id']:
                                    is_added = True
                                    break
                            if not is_added:
                                results[j][l].update({'phrase': products[j]})
                                duplicate_seller_items[results[i][k]['seller']['id']].append(results[j][l])
                        else:
                            duplicate_seller_items[results[i][k]['seller']['id']] = []
                            results[i][k].update({'phrase': products[i]})
                            duplicate_seller_items[results[i][k]['seller']['id']].append(results[i][k])
                            if not results[i][k]['id'] == results[j][l]['id']:
                                results[j][l].update({'phrase': products[j]})
                                duplicate_seller_items[results[i][k]['seller']['id']].append(results[j][l])
                        do_break = True
                        break
    sellers_to_remove = []
    for seller_id in duplicate_seller_items.keys():  # removing items from sellers with rating < 4*
        if not check_seller(seller_id, min_rating):
            sellers_to_remove.append(seller_id)
    for seller_id in sellers_to_remove:
        duplicate_seller_items.pop(seller_id)

    duplicate_seller_items_sorted = {}
    basket_combinations = []
    for k in sorted(duplicate_seller_items, key=lambda xy: len(duplicate_seller_items[xy]), reverse=True):
        duplicate_seller_items_sorted.update({k: duplicate_seller_items[k]})

    for item_list in duplicate_seller_items_sorted:
        missing_flags = []
        missing_flags.extend(products.copy())
        basket_combinations.append(duplicate_seller_items_sorted[item_list].copy())
        for item in duplicate_seller_items_sorted[item_list]:  # checking which items are missing in basket
            missing_flags.remove(item['phrase'])
        for missing_flag in missing_flags:  # adding missing items to basket -> cheapest item of each phrase
            for item in results[products.index(missing_flag)]:  # checking if seller's rating's good
                if check_seller(item['seller']['id'], min_rating):
                    item.update({'phrase': missing_flag})
                    basket_combinations[-1].append(item)
                    break
        # now we are going to combine baskets of multiple items from same seller with baskets from different seller
        missing_flags.clear()
        missing_flags.extend(products.copy())
        flags2 = []
        for item in duplicate_seller_items_sorted[item_list]:  # checking which items are missing in basket, again
            missing_flags.remove(item['phrase'])
        for item_list2 in duplicate_seller_items_sorted:
            # checking which items are in another's seller basket
            for item in duplicate_seller_items_sorted[item_list2]:
                flags2.append(item['phrase'])
            # if some seller has multiple items that are missing in basket, adding these items to the basket
            if len(set(flags2) & set(missing_flags)) > 1:
                basket_combinations.append(duplicate_seller_items_sorted[item_list].copy())
                # checking which items that are missing are in another's seller basket
                for flag in set(flags2) & set(missing_flags):
                    for item in duplicate_seller_items_sorted[item_list2]:
                        if item['phrase'] == flag:
                            basket_combinations[-1].append(item.copy())  # adding missing item
                            missing_flags.remove(flag)  # removing phrase from the missing list
                for missing_flag in missing_flags:  # fillng basket with cheapest items of each phrase
                    for item in results[products.index(missing_flag)]:  # checking if seller's rating's good
                        if check_seller(item['seller']['id'], min_rating):
                            item.update({'phrase': missing_flag})
                            basket_combinations[-1].append(item)
                            break

    overall_prices = []
    cheapest_items_combination = []
    # add cheapest items from each category
    for result in results:
        cheapest_items_combination.append(result[0])
    basket_combinations.append(cheapest_items_combination)
    # count overall prices
    for combination in basket_combinations:
        overall_price = 0
        delivery_prices = {}
        for item in combination:
            overall_price += Decimal(item['sellingMode']['price']['amount'])
            if not item['seller']['id'] in delivery_prices:
                delivery_prices[item['seller']['id']] = Decimal(item['delivery']['lowestPrice']['amount'])
            # taking the highest price of delivery of each basket's items
            elif Decimal(delivery_prices[item['seller']['id']]) < Decimal(item['delivery']['lowestPrice']['amount']):
                delivery_prices.update({delivery_prices[item['seller']['id']]: Decimal(item['delivery']['lowestPrice'][
                                                                                           'amount'])})
        for delivery_price in delivery_prices:
            overall_price += delivery_prices[delivery_price]
        overall_prices.append(overall_price)

    basket_combinations_sorted = [x for (y, x) in
                                  sorted(zip(overall_prices, basket_combinations), key=lambda pair: pair[0])]
    overall_prices_sorted = sorted(overall_prices)
    if len(basket_combinations_sorted) > 1:
        print('Trzy najtańsze zestawienia produktów to:')
    if len(basket_combinations_sorted) == 1:
        print('Nie znaleziono wspólnych sprzedawców wśród wyszukiwanych przedmiotów.')
        print('Oto lista najtańszych produktów: ')
    for i in range(len(basket_combinations_sorted)):
        print(str(i + 1) + ')')
        for item in basket_combinations_sorted[i]:
            print(item['name'])
            print('https://allegro.pl/oferta/' + item['id'])
        print(str(overall_prices_sorted[i]) + 'zł')
        print('-----------------------------------')
        if i == 2:
            break
else:
    print('Trzy najtańsze produkty to:')
    i = 0
    for item in results[0]:
        if i == 3:
            break
        if check_seller(item['seller']['id'], min_rating):
            print(item['name'])
            print(str(Decimal(item['sellingMode']['price']['amount'])
                      + Decimal(item['delivery']['lowestPrice']['amount'])) + 'zł')
            print('https://allegro.pl/oferta/' + item['id'])
            i = i + 1
