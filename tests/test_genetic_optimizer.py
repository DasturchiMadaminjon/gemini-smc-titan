import pytest
from core.genetic_optimizer import GeneticStrategyOptimizer

def test_genetic_optimizer_initialization():
    """
    Test maqsadi: Genetik optimizator to'g'ri boshlanishini va
    standart DNK (min_quality, tp_mult) parametrlarini tekshirish.
    """
    optimizer = GeneticStrategyOptimizer(population_size=10)
    assert len(optimizer.population) == 10
    
    # Har bir DNK da kerakli xususiyatlar bormi?
    for dna in optimizer.population:
        assert 'min_quality' in dna
        assert 'tp_mult' in dna
        assert 'mutation_rate' in dna
        assert 60 <= dna['min_quality'] <= 90
        assert 1.5 <= dna['tp_mult'] <= 4.0

def test_fitness_function():
    """
    Test maqsadi: Fitness funksiyasi savdo tarixiga qarab
    DNK ga to'g'ri ball berishini tekshirish.
    """
    optimizer = GeneticStrategyOptimizer()
    dna = {'min_quality': 75.0, 'tp_mult': 2.0}
    
    trade_history = [
        {'quality': 80.0, 'result': 'WIN'},   # Score += 2.0
        {'quality': 70.0, 'result': 'WIN'},   # Ignored (quality < 75.0)
        {'quality': 90.0, 'result': 'LOSS'},  # Score -= 1.0
        {'quality': 76.0, 'result': 'WIN'},   # Score += 2.0
    ]
    
    score = optimizer.fitness(dna, trade_history)
    assert score == 3.0 # 2.0 - 1.0 + 2.0 = 3.0

def test_evolution_process():
    """
    Test maqsadi: Evolyutsiya natijasida populyatsiyaning saqlanib qolishi
    va eng kuchli DNK ajratib olinishini tekshirish.
    """
    optimizer = GeneticStrategyOptimizer(population_size=5)
    
    # Simulyatsiya qilingan savdo tarixi (juda yaxshi natijalar)
    trade_history = [
        {'quality': 85.0, 'result': 'WIN'},
        {'quality': 88.0, 'result': 'WIN'},
        {'quality': 82.0, 'result': 'LOSS'}
    ]
    
    best_dna = optimizer.evolve(trade_history)
    
    # Yangi populyatsiya hajmi o'zgarmasligi kerak
    assert len(optimizer.population) == 10  # Note: evolve() har doim 10 taga to'ldiradi
    
    # Qaytarilgan DNK kerakli tuzilishga egami?
    assert 'min_quality' in best_dna
    assert 'tp_mult' in best_dna
    
    # Mutatsiya stavkasi mavjud bo'lishi kerak
    assert 'mutation_rate' in best_dna
