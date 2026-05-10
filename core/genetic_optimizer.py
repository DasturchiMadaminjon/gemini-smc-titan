import random

class GeneticStrategyOptimizer:
    """
    🧬 GENETIK KOD: Strategiya parametrlarini evolyutsiya qilish.
    Ushbu modul botning 'Sifat' (quality) va 'R:R' (Risk/Reward) nisbatlarini
    tarixiy ma'lumotlar asosida optimallashtiradi.
    """
    
    def __init__(self, population_size=10):
        self.population = []
        for _ in range(population_size):
            # Har bir 'shaxs' (individual) - bu botning DNKsi
            # DNA = {min_quality, tp_multiplier, sl_pips}
            self.population.append({
                'min_quality': random.uniform(60, 90),
                'tp_mult': random.uniform(1.5, 4.0),
                'mutation_rate': 0.1
            })

    def fitness(self, dna, trade_history):
        """
        🎯 Fitness funksiyasi: Ushbu DNK qanchalik foyda keltirdi?
        (Win-rate + Profit factor tahlili)
        """
        score = 0
        for trade in trade_history:
            if trade['quality'] >= dna['min_quality']:
                if trade['result'] == 'WIN':
                    score += dna['tp_mult']
                else:
                    score -= 1
        return score

    def evolve(self, trade_history):
        """
        🚀 Evolyutsiya: Eng yaxshi DNKlarni tanlash va yangi avlod yaratish.
        """
        # 1. Saralash (Selection)
        self.population.sort(key=lambda x: self.fitness(x, trade_history), reverse=True)
        elites = self.population[:2] # Eng yaxshi 2 ta 'ota-ona'
        
        new_population = elites.copy()
        
        # 2. Chatishtirish va Mutatsiya (Crossover & Mutation)
        while len(new_population) < 10:
            parent1, parent2 = random.sample(elites, 2)
            child = {
                'min_quality': (parent1['min_quality'] + parent2['min_quality']) / 2,
                'tp_mult': random.choice([parent1['tp_mult'], parent2['tp_mult']]),
                'mutation_rate': parent1['mutation_rate']
            }
            
            # Tasodifiy mutatsiya (Yangi DNK elementlari qo'shilishi)
            if random.random() < child['mutation_rate']:
                child['min_quality'] += random.uniform(-5, 5)
                child['tp_mult'] += random.uniform(-0.5, 0.5)
                
            new_population.append(child)
            
        self.population = new_population
        return self.population[0] # Yangi avlodning eng kuchli vakili

# 📝 IZOH (G.KOD):
# 1. Population: Bot bir vaqtning o'zida turli xil sozlamalar bilan 'hayolan' savdo qiladi.
# 2. Fitness: Qaysi sozlamalar eng ko'p foyda va eng kam zarar keltirsa, o'sha 'DNK' yashab qoladi.
# 3. Mutation: Tizim doim bir xil qolib ketmasligi uchun vaqti-vaqti bilan yangi 'g'oyalar' (tasodifiy o'zgarishlar) kiritadi.
# 4. Survivor: Eng kuchli sozlama botning asosiy config/settings.yaml fayliga yoziladi.
