import numpy as np
import matplotlib.pyplot as plt


def count_eaten_haystacks(n):
    """
    Подсчитывает количество стогов сена, которые будут съедены овечкой Долли и всеми её клонами.
    
    Логика:
    - Если n < 4: выкидывает n стогов (не ест) -> возвращаем 0
    - Если n >= 4:
      - Если n делится на 5:
        - Сбрасывает n/5 стогов в овраг (не ест)
        - Сама обрабатывает 3n/5 стогов
        - Клон обрабатывает n/5 стогов
      - Иначе:
        - Съедает 4 стога
        - Обрабатывает оставшиеся n-4 стогов
    """
    # Базовый случай: если стогов меньше 4, овечка выкидывает их (не ест)
    if n < 4:
        return 0
    
    # Если n делится на 5
    if n % 5 == 0:
        # Сбрасывает n/5 стогов в овраг (не ест)
        # Сама обрабатывает 3n/5 стогов
        # Клон обрабатывает n/5 стогов
        return count_eaten_haystacks(3 * n // 5) + count_eaten_haystacks(n // 5)
    else:
        # Съедает 4 стога и обрабатывает оставшиеся n-4 стогов
        return 4 + count_eaten_haystacks(n - 4)


def plot_histogram(start_n=1, end_n=100):
    """
    Строит гистограмму зависимости количества съеденных стогов от исходного количества.
    
    Args:
        start_n: начальное значение n (по умолчанию 1)
        end_n: конечное значение n (по умолчанию 100)
    """
    # Создаем массив значений n
    n_values = np.arange(start_n, end_n + 1)
    
    # Вычисляем количество съеденных стогов для каждого n
    eaten_values = np.array([count_eaten_haystacks(n) for n in n_values])
    
    # Создаем гистограмму
    plt.figure(figsize=(12, 6))
    plt.bar(n_values, eaten_values, width=0.8, color='skyblue', edgecolor='navy', alpha=0.7)
    plt.xlabel('Количество стогов сена (n)', fontsize=12)
    plt.ylabel('Количество съеденных стогов', fontsize=12)
    plt.title('Зависимость количества съеденных стогов от исходного количества\n(Овечка Долли и её клоны)', fontsize=14)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.show()


def main():
    """Основная функция - запрашивает количество стогов и выводит результат или строит гистограмму"""
    print("Выберите режим:")
    print("1 - Вычислить количество съеденных стогов для одного значения")
    print("2 - Построить гистограмму")
    
    try:
        choice = input("Ваш выбор (1 или 2): ").strip()
        
        if choice == "1":
            n = int(input("Введите количество стогов сена: "))
            if n < 0:
                print("Количество стогов не может быть отрицательным!")
                return
            result = count_eaten_haystacks(n)
            print(result)
        elif choice == "2":
            start_n = int(input("Введите начальное значение n (по умолчанию 1): ") or "1")
            end_n = int(input("Введите конечное значение n (по умолчанию 100): ") or "100")
            if start_n < 0 or end_n < 0 or start_n > end_n:
                print("Некорректные значения!")
                return
            print("Построение гистограммы...")
            plot_histogram(start_n, end_n)
        else:
            print("Неверный выбор!")
    except ValueError:
        print("Пожалуйста, введите целое число")
    except KeyboardInterrupt:
        print("\nВыход из программы...")


if __name__ == "__main__":
    main()

